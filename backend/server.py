from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict
import json
import uuid
from datetime import datetime
from openai import OpenAI
from context import build_system_prompt
from rag import rag_service

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize HF Inference client (OpenAI-compatible)
HF_TOKEN = os.getenv("HF_TOKEN", "")
hf_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# Model selection
HF_MODEL_ID = os.getenv("HF_MODEL_ID", "meta-llama/Llama-3.1-8B-Instruct")

# Memory storage configuration (local only — no S3 for HF Spaces)
MEMORY_DIR = os.getenv("MEMORY_DIR", "/data/memory")


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class Message(BaseModel):
    role: str
    content: str
    timestamp: str


@app.on_event("startup")
async def startup_event():
    """Initialize RAG service on startup."""
    rag_service.initialize()


# Memory management functions
def get_memory_path(session_id: str) -> str:
    return f"{session_id}.json"


def load_conversation(session_id: str) -> List[Dict]:
    """Load conversation history from local storage"""
    file_path = os.path.join(MEMORY_DIR, get_memory_path(session_id))
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []


def save_conversation(session_id: str, messages: List[Dict]):
    """Save conversation history to local storage"""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    file_path = os.path.join(MEMORY_DIR, get_memory_path(session_id))
    with open(file_path, "w") as f:
        json.dump(messages, f, indent=2)


def call_llm(conversation: List[Dict], user_message: str) -> str:
    """Call HF Inference API via OpenAI-compatible client"""

    # Retrieve relevant context for this query
    rag_context = rag_service.retrieve(user_message)
    system_prompt = build_system_prompt(rag_context)

    # Build messages with dynamic system prompt
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (limit to last 10 messages for token safety)
    for msg in conversation[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    try:
        response = hf_client.chat.completions.create(
            model=HF_MODEL_ID,
            messages=messages,
            max_tokens=2000,
            temperature=0.7,
            top_p=0.9,
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


@app.get("/api/info")
async def info():
    return {
        "message": "AI Digital Twin API (Powered by HF Inference)",
        "memory_enabled": True,
        "storage": "local",
        "ai_model": HF_MODEL_ID,
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "ai_model": HF_MODEL_ID,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Load conversation history
        conversation = load_conversation(session_id)

        # Call LLM for response
        assistant_response = call_llm(conversation, request.message)

        # Update conversation history
        conversation.append(
            {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()}
        )
        conversation.append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Save conversation
        save_conversation(session_id, conversation)

        return ChatResponse(response=assistant_response, session_id=session_id)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Retrieve conversation history"""
    try:
        conversation = load_conversation(session_id)
        return {"session_id": session_id, "messages": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve Next.js static export — must be last so API routes take priority
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)

---
title: AI Digital Twin
emoji: 🤖
colorFrom: gray
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# AI Digital Twin

A context-adaptive persona engine that creates a high-fidelity AI representation of a professional. Visitors interact with the digital twin through a conversational chat interface, receiving accurate responses grounded in real career data, communication style, and professional history via Retrieval-Augmented Generation (RAG).

**Live:** [https://huggingface.co/spaces/hopeogbons/career_conversation](https://huggingface.co/spaces/hopeogbons/career_conversation)

---

## Architecture

A single-container Docker deployment on Hugging Face Spaces that bundles the frontend, backend, RAG pipeline, and embedding model into one image.

```
                            ┌───────────┐
                            │  Browser  │
                            └─────┬─────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 HF Spaces Docker Container (port 7860)              │
│                                                                     │
│                      ┌──────────────────┐                           │
│                      │  FastAPI (Uvicorn)│                           │
│                      └────────┬─────────┘                           │
│                               │                                     │
│              ┌────────────────┼────────────────┐                    │
│              │                │                │                     │
│              ▼                ▼                ▼                     │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────┐           │
│  │ Static Files  │  │  /api/chat     │  │ /api/convo   │           │
│  │ Next.js export│  │  Chat handler  │  │ History API  │           │
│  │ served at /   │  └────────┬───────┘  └──────────────┘           │
│  └───────────────┘           │                                      │
│                     ┌────────┼────────┐                             │
│                     │        │        │                              │
│                     ▼        ▼        ▼                              │
│            ┌─────────┐ ┌─────────┐ ┌───────────────┐                │
│            │ Memory  │ │  RAG    │ │Persona Engine │                │
│            │ Manager │ │ Service │ │               │                │
│            │         │ │         │ │ Static prompt │                │
│            │ /data/  │ │ChromaDB │ │ + style.txt   │                │
│            │ memory/ │ │ + ONNX  │ │ + RAG context │                │
│            │ {id}    │ │MiniLM-  │ │ + timestamp   │                │
│            │ .json   │ │ L6-v2   │ │               │                │
│            │         │ │         │ │ Builds system │                │
│            │ Load &  │ │Top-5    │ │ prompt per    │                │
│            │ save    │ │cosine   │ │ request       │                │
│            │ convo   │ │retrieval│ └───────┬───────┘                │
│            │ history │ │         │         │                         │
│            └─────────┘ │ Sources:│         ▼                         │
│                        │ facts   │ ┌───────────────────┐            │
│                        │ summary │ │ HF Inference API  │            │
│                        │ linkedin│ │ (external call)   │            │
│                        └─────────┘ │                   │            │
│                                    │ Llama 3.1 8B      │            │
│                                    │ via HF_TOKEN       │            │
│                                    └───────────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## System Design

### RAG Pipeline (Retrieval-Augmented Generation)

Rather than stuffing the entire persona dataset into every LLM prompt, the system uses a vector-based retrieval pipeline to inject only the most relevant context per query. This reduces token usage and improves response precision.

**Data Ingestion and Chunking**

Source data is split into semantically meaningful chunks at startup:

| Source | Chunking Strategy | Resulting Chunks |
|---|---|---|
| `summary.txt` | Split by ALL-CAPS section headers. `NOTABLE PROJECTS` is further split into individual numbered projects. | ~12 chunks (career sections, individual projects) |
| `facts.json` | Converted to natural-language sentences grouped by category (basic info, specialties, education, technologies, industries). | 5 chunks |
| `linkedin.pdf` | Parsed via PyPDF for text extraction. Used as supplementary data. | Raw text (not chunked separately) |
| `style.txt` | Loaded as a static communication style directive injected into every prompt. | Not chunked (always included) |

**Vector Store**

- **ChromaDB** with persistent storage at `/data/chroma_db`
- **Embedding model:** `all-MiniLM-L6-v2` via ONNX Runtime (384-dimensional sentence embeddings)
- **Collection metadata** stores an MD5 hash of the source data, enabling automatic index rebuild only when the underlying data changes
- Top-5 nearest neighbors retrieved per query via cosine similarity

**Index Lifecycle Management**

On startup, the RAG service:
1. Computes an MD5 hash of the current source data (`summary` + `facts`)
2. Checks if the existing ChromaDB collection's stored hash matches
3. If matched, loads the index (fast path, no re-embedding)
4. If mismatched or missing, rebuilds the index from scratch with retry logic (3 attempts, linear backoff)

### Persona Engine

The system prompt is constructed dynamically per request:

1. **Static scaffold** defines the twin's role, behavioral constraints, and communication style
2. **RAG context placeholder** is filled with the top-5 retrieved chunks relevant to the user's query
3. **Conversation history** (last 10 messages) is appended for multi-turn coherence
4. **Timestamp injection** provides temporal awareness

**Behavioral Guardrails:**
- Anti-hallucination: the model is instructed to only use information present in the provided context
- Anti-jailbreak: explicit instructions to reject prompt override attempts
- Professionalism enforcement: the model steers conversations back to professional topics when needed
- Persona consistency: the model presents itself as the person, not as a generic assistant

### Conversation Memory

Each conversation is persisted as a JSON file keyed by session ID, stored locally at `/data/memory/{session_id}.json`.

The session ID is generated server-side on first message and returned to the client, which includes it in subsequent requests. This keeps the backend stateless across requests while maintaining conversational continuity.

### Chat Frontend

Built as a Next.js static export for zero-runtime overhead:

- **Conversation starters:** pre-defined prompt chips for first-time visitors to reduce blank-page friction
- **Markdown rendering:** assistant messages rendered with `react-markdown` supporting bold, lists, code blocks, and headings
- **Auto-resizing textarea:** input grows with content up to a maximum height, with Enter to send and Shift+Enter for new lines
- **Typing indicator:** animated bounce dots displayed during LLM inference
- **Avatar system:** circular headshot avatars on assistant messages with an online status indicator; generic user icon on user messages
- **Viewport-locked layout:** the page uses `h-screen` with flex layout to prevent page-level scrolling; only the message area scrolls

---

## Best Practices

### Docker and Containerization

- **Multi-stage build:** Stage 1 builds the Next.js static export in a Node.js Alpine image; Stage 2 copies only the built output into a Python slim image. This keeps the final image small and free of build tooling.
- **Pre-baked embedding model:** The ChromaDB ONNX model (~79MB) is downloaded and cached during `docker build`, not at runtime. This prevents cold-start timeouts on HF Spaces (which enforces a startup deadline).
- **Non-root execution:** The container runs as UID 1000 (`user`), matching HF Spaces' security requirement. File ownership is explicitly set during build.
- **Deterministic installs:** `npm ci` for frontend (lockfile-exact), `pip install --no-cache-dir` for backend (no stale cache).

### Reliability

- **Retry with backoff:** RAG index construction retries up to 3 times with linear backoff (10s, 20s, 30s). Failed collections are cleaned up before retry to avoid partial state.
- **Graceful degradation:** If the RAG service fails to initialize, the system continues to operate (retrieval returns empty string, and the persona engine falls back to the static prompt).
- **Data change detection:** MD5 hashing of source data prevents unnecessary index rebuilds, reducing startup time on subsequent container restarts when data hasn't changed.

### Security

- **No hardcoded credentials:** The HF token is injected via Space secrets (environment variables), never committed to source control.
- **CORS configuration:** Configurable allowed origins via the `CORS_ORIGINS` environment variable, defaulting to permissive for development.
- **Input guardrails:** The system prompt includes explicit jailbreak resistance instructions to prevent prompt injection and unauthorized behavior.
- **Telemetry disabled:** ChromaDB's anonymized telemetry is explicitly turned off to prevent any data leakage from the container.

### Frontend

- **Static export:** `next build` with `output: "export"` produces a fully static site (HTML, CSS, JS) with zero server-side runtime. This enables serving directly from FastAPI's `StaticFiles` middleware within the same container.
- **Viewport-locked layout:** Uses `h-screen` + `overflow-hidden` on the root element with `min-h-0` on flex children to prevent double scrollbars and ensure the chat fills available space.
- **Relative API calls:** `NEXT_PUBLIC_API_URL` is set to empty string during Docker build, causing the frontend to make relative API calls (`/api/chat`). This works because FastAPI serves both the static files and the API from the same origin on port 7860.

### Backend

- **Single-file server:** `server.py` handles all API routes, CORS, static file serving, and LLM orchestration in one module. This simplifies the Docker build and keeps the deployment unit minimal.
- **OpenAI-compatible client:** The HF Inference API is accessed via the standard OpenAI Python SDK, making it straightforward to swap LLM providers (HF, OpenAI, local) by changing the base URL and API key.
- **Conversation context window:** Only the last 10 messages are sent to the LLM, preventing token limit issues on long conversations while preserving recent context.
- **API-last static mount:** `StaticFiles` is mounted at `/` as the last route, ensuring `/api/*` routes take priority and aren't shadowed by the catch-all static file handler.

---

## Project Structure

```
├── backend/
│   ├── server.py              # FastAPI application (API + static serving)
│   ├── context.py             # Dynamic system prompt builder
│   ├── rag.py                 # RAG pipeline (ChromaDB + chunking)
│   ├── resources.py           # Data loader (PDF, JSON, text files)
│   ├── requirements.txt       # Python dependencies
│   └── data/
│       ├── facts.json         # Structured biographical facts
│       ├── summary.txt        # Professional summary, skills, projects
│       ├── style.txt          # Communication style directive
│       └── linkedin.pdf       # LinkedIn profile (PDF)
├── frontend/
│   ├── app/
│   │   ├── page.tsx           # Home page (profile hero + chat)
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Global styles (Tailwind)
│   ├── components/
│   │   └── twin.tsx           # Chat component (messages, input, starters)
│   ├── public/
│   │   └── hopeogbons.png     # Headshot avatar
│   ├── next.config.ts         # Static export configuration
│   └── package.json
├── Dockerfile                 # Multi-stage build (Node.js + Python)
├── .dockerignore              # Docker build exclusions
└── .env.example               # Environment variable template
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, react-markdown, Lucide icons |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic |
| RAG | ChromaDB, ONNX Runtime, all-MiniLM-L6-v2, PyPDF |
| AI | HF Inference API, Llama 3.1 8B Instruct |
| Infrastructure | Docker, Hugging Face Spaces |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/info` | Service metadata (model, storage type) |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/chat` | Send a message, receive AI response |
| `GET` | `/api/conversation/{session_id}` | Retrieve full conversation history |

### Chat Request

```json
{
  "message": "Tell me about your experience with AI",
  "session_id": "optional-existing-session-id"
}
```

### Chat Response

```json
{
  "response": "I've been working extensively with AI systems...",
  "session_id": "generated-or-existing-session-id"
}
```

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The backend runs on `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:3000` and connects to the backend at `http://localhost:8000`.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HF_TOKEN` | (required) | Hugging Face API token |
| `HF_MODEL_ID` | `meta-llama/Llama-3.1-8B-Instruct` | Model for HF Inference API |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `MEMORY_DIR` | `/data/memory` | Local conversation storage path |
| `CHROMA_DB_PATH` | `/data/chroma_db` | ChromaDB persistent storage path |

Create `backend/.env` for local overrides:

```
HF_TOKEN=hf_xxx
MEMORY_DIR=../memory
```

---

## Deployment

### Docker (Local)

```bash
docker build -t digital-twin .
docker run -p 7860:7860 -e HF_TOKEN=hf_xxx digital-twin
```

Open `http://localhost:7860`.

### Hugging Face Spaces

1. Create a new Space on [huggingface.co](https://huggingface.co/new-space) with **Docker** SDK
2. Add the `HF_TOKEN` secret in the Space settings under **Variables and secrets**
3. Push the repository to the Space:

```bash
git remote add hf https://huggingface.co/spaces/<username>/<space-name>
git push hf main
```

HF Spaces will automatically build the Docker image and deploy. The app will be available at `https://<username>-<space-name>.hf.space`.

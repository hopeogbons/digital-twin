import hashlib
import json
import os
import re
import time

import chromadb
from chromadb.config import Settings

from resources import summary, facts

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/data/chroma_db")
COLLECTION_NAME = "digital_twin"
HASH_META_KEY = "data_hash"


def chunk_summary(text: str) -> list[dict]:
    """Split summary.txt by ALL-CAPS section headers, then split NOTABLE PROJECTS into individual projects."""
    sections = re.split(r"\n(?=[A-Z][A-Z &]+\n)", text)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n", 1)
        header = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        if header == "NOTABLE PROJECTS":
            # Split into individual projects by numbered pattern
            projects = re.split(r"\n(?=\d+\.\s)", body)
            for project in projects:
                project = project.strip()
                if project:
                    chunks.append({"text": f"NOTABLE PROJECTS\n{project}", "section": "projects"})
        elif header in ("FORWARD-DEPLOYED CLIENT WORK (via Andela)", "FORWARD-DEPLOYED CLIENT WORK"):
            # Keep as one chunk
            chunks.append({"text": section, "section": "client_work"})
        elif header == "EARLIER CAREER":
            chunks.append({"text": section, "section": "earlier_career"})
        elif header == "CERTIFICATIONS":
            chunks.append({"text": section, "section": "certifications"})
        else:
            chunks.append({"text": section, "section": header.lower().replace(" ", "_")})

    return chunks


def chunk_facts(data: dict) -> list[dict]:
    """Convert facts.json into natural-language chunks."""
    chunks = []

    # Basic info
    basic = (
        f"Hope Ogbons's basic info: Full name is {data['full_name']}, goes by {data['name']}. "
        f"Current role: {data['current_role']}. "
        f"Employers: {', '.join(data['current_employers'])}. "
        f"Location: {data['location']}. "
        f"Email: {data['email']}. Phone: {data['phone']}. "
        f"LinkedIn: {data['linkedin']}. GitHub: {data['github']}. "
        f"Years of experience: {data['years_experience']}."
    )
    chunks.append({"text": basic, "section": "basic_info"})

    # Specialties
    specs = "Hope Ogbons's specialties: " + ", ".join(data["specialties"]) + "."
    chunks.append({"text": specs, "section": "specialties"})

    # Education
    edu_lines = [f"{e['degree']} from {e['institution']}" for e in data["education"]]
    edu = "Hope Ogbons's education: " + "; ".join(edu_lines) + "."
    chunks.append({"text": edu, "section": "education"})

    # Technologies
    tech = "Hope Ogbons's key technologies: " + ", ".join(data["key_technologies"]) + "."
    chunks.append({"text": tech, "section": "technologies"})

    # Industries and interests
    ind = (
        "Hope Ogbons's industries: " + ", ".join(data["industries"]) + ". "
        "Personal interests: " + ", ".join(data["personal_interests"]) + "."
    )
    chunks.append({"text": ind, "section": "industries_interests"})

    return chunks


class RAGService:
    def __init__(self):
        self.client = None
        self.collection = None

    def initialize(self, max_retries: int = 3):
        """Initialize ChromaDB and build/load index with retry for ONNX model download."""
        self.client = chromadb.Client(Settings(
            persist_directory=CHROMA_DB_PATH,
            is_persistent=True,
            anonymized_telemetry=False,
        ))

        current_hash = self._compute_data_hash()

        # Check if collection exists and data hash matches
        existing_collections = [c.name for c in self.client.list_collections()]
        if COLLECTION_NAME in existing_collections:
            self.collection = self.client.get_collection(COLLECTION_NAME)
            stored = self.collection.metadata or {}
            if stored.get(HASH_META_KEY) == current_hash:
                count = self.collection.count()
                print(f"RAG index loaded: {count} chunks (hash match)", flush=True)
                return
            # Hash mismatch — rebuild
            self.client.delete_collection(COLLECTION_NAME)
            print("RAG data changed, rebuilding index...", flush=True)

        for attempt in range(1, max_retries + 1):
            try:
                self._build_index(current_hash)
                return
            except Exception as e:
                if attempt < max_retries:
                    wait = 10 * attempt
                    print(f"RAG build attempt {attempt} failed: {e}. Retrying in {wait}s...", flush=True)
                    # Clean up failed collection before retry
                    try:
                        self.client.delete_collection(COLLECTION_NAME)
                    except Exception:
                        pass
                    time.sleep(wait)
                else:
                    raise

    def _build_index(self, data_hash: str):
        """Chunk all sources and add to ChromaDB."""
        self.collection = self.client.create_collection(
            name=COLLECTION_NAME,
            metadata={HASH_META_KEY: data_hash},
        )

        all_chunks = chunk_summary(summary) + chunk_facts(facts)

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(all_chunks):
            ids.append(f"chunk_{i}")
            documents.append(chunk["text"])
            metadatas.append({"section": chunk["section"]})

        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"RAG index built: {len(all_chunks)} chunks", flush=True)

    def retrieve(self, query: str, top_k: int = 5) -> str:
        """Retrieve top-k relevant chunks and return formatted context string."""
        if not self.collection:
            return ""

        results = self.collection.query(query_texts=[query], n_results=top_k)

        if not results or not results["documents"] or not results["documents"][0]:
            return ""

        context_parts = []
        for doc in results["documents"][0]:
            context_parts.append(doc)

        return "\n\n".join(context_parts)

    def _compute_data_hash(self) -> str:
        """MD5 hash of source data to detect changes."""
        hasher = hashlib.md5()
        hasher.update(summary.encode("utf-8"))
        hasher.update(json.dumps(facts, sort_keys=True).encode("utf-8"))
        return hasher.hexdigest()


# Module-level singleton
rag_service = RAGService()

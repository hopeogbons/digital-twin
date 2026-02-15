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

A context-adaptive persona engine that creates a high-fidelity AI representation of a professional. Visitors interact with the digital twin through a chat interface, getting accurate responses grounded in real career data, communication style, and professional history.

**Live (HF Spaces):** Deployed as a Docker Space on Hugging Face
**Live (AWS):** [https://d5zo5ki02wqtq.cloudfront.net](https://d5zo5ki02wqtq.cloudfront.net)

## Architecture

### Hugging Face Spaces (Docker)

```
Browser → HF Spaces (Docker Container)
              ├── FastAPI (serves static + API)
              ├── Next.js static export (frontend)
              ├── HF Inference API (Llama 3.1 8B)
              └── /data volume (conversation memory)
```

### AWS (Lambda)

```
Browser → CloudFront (CDN) → S3 (Static Frontend)
                                    ↓
                            API Gateway (HTTP)
                                    ↓
                           AWS Lambda (FastAPI)
                                    ↓
                         AWS Bedrock (Nova Lite)
                                    ↓
                        S3 (Conversation Memory)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS, react-markdown |
| Backend | Python 3.12, FastAPI |
| AI | HF Inference API (Llama 3.1 8B) / AWS Bedrock (Nova Lite) |
| Infrastructure | Docker (HF Spaces) / Terraform + AWS Lambda + CloudFront |
| CI/CD | Git push to HF Space / GitHub Actions with OIDC |

## Key Features

### Persona Engine
- Dynamically loads biographical facts, LinkedIn profile, communication style, and professional summary into the system prompt
- Maintains conversation context across stateless Lambda invocations via S3 JSON persistence
- Supports multi-turn conversations with a 20-message context window
- Guardrails against hallucination, jailbreak attempts, and unprofessional interactions

### Chat UI
- Profile hero section with headshot and professional title
- Circular avatar headshots on all assistant messages with online status indicator
- Clickable conversation starter chips for first-time visitors
- Markdown rendering for AI responses (bold, lists, code blocks, headings)
- Multi-line textarea input with auto-resize (Enter to send, Shift+Enter for new line)
- Responsive chat height that adapts to screen size
- Animated typing indicator during AI response generation

### Infrastructure
- Fully reproducible via Terraform with multi-environment support (dev/test/prod)
- Serverless compute with AWS Lambda — zero infrastructure maintenance
- Global edge delivery via CloudFront with SSL/TLS and custom domain support
- OIDC-based GitHub Actions deployment — no hardcoded AWS credentials
- API throttling (burst: 10, rate: 5) to control costs

## Project Structure

```
├── backend/
│   ├── server.py              # FastAPI application
│   ├── lambda_handler.py      # Lambda entry point (Mangum)
│   ├── context.py             # System prompt builder
│   ├── resources.py           # Data loader (PDF, facts, style)
│   ├── deploy.py              # Lambda package builder (Docker)
│   ├── requirements.txt
│   └── data/
│       ├── facts.json         # Biographical facts
│       ├── summary.txt        # Professional summary, skills, projects
│       ├── style.txt          # Communication style guide
│       └── linkedin.pdf       # LinkedIn profile
├── frontend/
│   ├── app/
│   │   ├── page.tsx           # Home page with profile hero
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Global styles
│   ├── components/
│   │   └── twin.tsx           # Chat component
│   ├── public/
│   │   └── hopeogbons.png     # Headshot avatar
│   └── package.json
├── terraform/
│   ├── main.tf                # Lambda, API GW, CloudFront, S3, Route53
│   ├── variables.tf           # Configurable inputs
│   ├── outputs.tf             # Deployment URLs
│   ├── backend.tf             # S3 state backend
│   └── versions.tf            # Provider versions
├── scripts/
│   ├── deploy.sh              # Deployment orchestration
│   └── destroy.sh             # Infrastructure teardown
└── .github/workflows/
    ├── deploy.yml             # Auto-deploy on push to main
    └── destroy.yml            # Manual teardown with confirmation
```

## Local Development

### Prerequisites

- Python 3.12
- Node.js 20+
- AWS CLI configured with Bedrock access
- Docker (for Lambda packaging only)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The backend runs on `http://localhost:8000`. Conversations save locally to `../memory/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:3000` and connects to the backend automatically.

### Environment Variables

No `.env` file is required for local development (with HF token). Defaults handle everything:

| Variable | Default | Description |
|---|---|---|
| `HF_TOKEN` | (required) | Hugging Face API token |
| `HF_MODEL_ID` | `meta-llama/Llama-3.1-8B-Instruct` | HF model to use |
| `CORS_ORIGINS` | `*` | Allowed origins |
| `MEMORY_DIR` | `/data/memory` | Conversation storage path |

To override, create `backend/.env`:

```
HF_TOKEN=hf_xxx
HF_MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
MEMORY_DIR=../memory
```

## Deployment

### Hugging Face Spaces (Docker)

```bash
# Build and run locally
docker build -t digital-twin .
docker run -p 7860:7860 -e HF_TOKEN=hf_xxx digital-twin

# Open http://localhost:7860
```

Push to a HF Space repo to deploy. Set `HF_TOKEN` as a Space secret.

### Direct Deploy to AWS (from local machine)

```bash
DEFAULT_AWS_REGION=us-east-2 ./scripts/deploy.sh dev
```

This builds the Lambda package, applies Terraform, builds the frontend, and syncs to S3.

### GitHub Actions

Push to `main` triggers automatic deployment. Manual dispatch supports environment selection (dev/test/prod).

Required GitHub Secrets:

| Secret | Description |
|---|---|
| `AWS_ACCOUNT_ID` | 12-digit AWS account ID |
| `DEFAULT_AWS_REGION` | Target region (e.g., `us-east-2`) |
| `AWS_ROLE_ARN` | IAM OIDC role ARN for GitHub Actions |

### AWS Prerequisites

- S3 bucket for Terraform state: `twin-terraform-state-<ACCOUNT_ID>`
- DynamoDB table for state locking: `twin-terraform-locks`
- IAM OIDC identity provider for GitHub Actions
- Bedrock model access enabled for Nova models

### Teardown

```bash
DEFAULT_AWS_REGION=us-east-2 ./scripts/destroy.sh dev
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/info` | Service info (model, storage type) |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/chat` | Send a message, get AI response |
| `GET` | `/api/conversation/{session_id}` | Retrieve conversation history |

### Chat Request

```json
{
  "message": "Tell me about your experience with AWS",
  "session_id": "optional-existing-session-id"
}
```

### Chat Response

```json
{
  "response": "I've been working extensively with AWS...",
  "session_id": "generated-or-existing-session-id"
}
```

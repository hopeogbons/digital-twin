# AI Digital Twin

A context-adaptive persona engine that creates a high-fidelity AI representation of a professional. Visitors interact with the digital twin through a chat interface, getting accurate responses grounded in real career data, communication style, and professional history.

**Live:** [https://d5zo5ki02wqtq.cloudfront.net](https://d5zo5ki02wqtq.cloudfront.net)

## Architecture

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
| Backend | Python 3.12, FastAPI, Mangum (Lambda adapter) |
| AI | AWS Bedrock (Amazon Nova Lite), dynamic prompt engineering |
| Infrastructure | Terraform, AWS Lambda, API Gateway v2, CloudFront, S3, Route53, ACM |
| CI/CD | GitHub Actions with OIDC authentication |

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

No `.env` file is required for local development. Defaults handle everything:

| Variable | Default | Description |
|---|---|---|
| `USE_S3` | `false` | Use local file storage instead of S3 |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origin |
| `BEDROCK_MODEL_ID` | `amazon.nova-lite-v1:0` | AWS Bedrock model |
| `DEFAULT_AWS_REGION` | `us-east-1` | AWS region |

To override, create `backend/.env`:

```
DEFAULT_AWS_REGION=us-east-2
BEDROCK_MODEL_ID=amazon.nova-micro-v1:0
```

## Deployment

### Direct Deploy (from local machine)

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
| `GET` | `/` | Service info (model, storage type) |
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Send a message, get AI response |
| `GET` | `/conversation/{session_id}` | Retrieve conversation history |

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

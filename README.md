# Pharma Manager

Pharma Manager is a safety-focused internal pharmaceutical assistant preview. It provides a browser chat experience for product and medical-information questions, routes requests through a server-side API boundary, and applies deterministic safety classification before any model provider is used.

## Architecture

```text
Browser
  |
  v
Next.js web app :3000
  |
  | POST /api/chat
  v
Spring Boot core API :8080
  |
  | POST /v1/chat
  v
Python Pharma AI service :8000
  |
  v
Controlled safety workflow
```

The frontend never calls an LLM provider directly. The Spring Boot service owns conversation persistence and audit events, while the Python service owns risk classification and response policy.

## Current capabilities

- Next.js, React, and TypeScript assistant interface.
- Validated `POST /api/chat` gateway with a 1–4,000 character question limit.
- Spring Boot conversation and message API with Flyway-managed PostgreSQL tables.
- Python/FastAPI health and chat endpoints.
- Deterministic handling for emergency and high-risk questions, including overdose, breathing difficulty, dosage, pregnancy, side effects, contraindications, and adverse events.
- Trace IDs for AI-service responses and audit-oriented metadata.
- Prisma schema for conversation and message data.

## Safety status

This is a preview, not a diagnostic, treatment, or emergency-response system. Emergency questions receive an urgent-care response, and the service fails closed when no approved model provider is configured. No OpenAI key or model credential is exposed to the frontend, and the project does not implement an unofficial ChatGPT browser-session or OAuth-token exchange.

Approved-document retrieval, citations, authentication, consent, production model configuration, and full Java/PostgreSQL integration verification remain future work.

## Run locally

Install and verify the frontend dependencies:

```bash
npm ci
./init.sh
```

Start the frontend:

```bash
npm run dev
```

The web app runs at `http://localhost:3000`.

The Python service can be started separately:

```bash
cd src/ai-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The Spring Boot core API requires Java 21, Maven, and PostgreSQL. Copy `.env.example` to configure local service URLs and database access.

## Project layout

- `src/frontend/` — Next.js application and `/api/chat` gateway.
- `src/backend/` — Spring Boot core API, persistence, and audit workflow.
- `src/ai-backend/` — Python/FastAPI safety workflow and provider boundary.
- `prisma/schema.prisma` — Prisma data model for conversations and messages.
- `docs/IMPLEMENTED_SERVICES.md` — detailed service, endpoint, and verification notes.

## Verification

The standard startup script runs dependency installation, linting, TypeScript checks, frontend tests, and a production build. Spring Boot verification additionally requires Java 21, Maven, and PostgreSQL.

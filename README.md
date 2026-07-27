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
  |                         \
  |                          v
  |                    Core PostgreSQL
  |                    app_user,
  |                    business_session
  |
  | POST /v1/chat
  v
Python Pharma AI service :8000
  |
  +--> AI PostgreSQL
       chat_session, chat_message,
       providers, models, prompts
```

The frontend never calls an LLM provider directly. Spring Boot owns users and business sessions, while Python owns all AI state, risk classification, and response policy. Spring Boot treats `chatSessionId` as opaque.

## Current capabilities

- Next.js, React, and TypeScript assistant interface.
- Validated `POST /api/chat` gateway with a 1–4,000 character question limit.
- Spring Boot user and business-session API with Flyway-managed core PostgreSQL tables.
- Python/FastAPI health and chat endpoints.
- AI-owned PostgreSQL persistence for chat sessions and messages, with provider/model and versioned-prompt tables.
- Deterministic handling for emergency and high-risk questions, including overdose, breathing difficulty, dosage, pregnancy, side effects, contraindications, and adverse events.
- Trace IDs for AI-service responses and audit-oriented metadata.
- Separate core and AI PostgreSQL database configuration.

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

## Run with Docker Compose

Docker Compose provisions separate core and AI PostgreSQL databases, the Redis cache service reserved by the recommended architecture, and the three application services.

```bash
docker compose up --build
```

The frontend is available at `http://localhost:3000`. Core PostgreSQL is exposed on `localhost:5432`, AI PostgreSQL on `localhost:5433`, and Redis on `localhost:6379`. Flyway creates only core tables; the AI service applies its own schema to the AI database.

For local OIDC testing, Keycloak is available at `http://localhost:8081`. The imported `pharma-manager` realm provides `user/user` (`PHARMA_USER`) and `admin/admin` (`PHARMA_USER`, `PHARMA_ADMIN`) test accounts. Start it with `docker compose up keycloak`; these credentials are development-only.

To start only the data services:

```bash
docker compose up core-postgres ai-postgres redis
```

Stop the stack with `docker compose down`. Add `-v` only when the local PostgreSQL and Redis data volumes should also be removed.

## Project layout

- `src/frontend/` — Next.js application and `/api/chat` gateway.
- `src/backend/` — Spring Boot core API, business persistence, and chat relay.
- `src/ai-backend/` — Python/FastAPI safety workflow and provider boundary.
- `src/ai-backend/migrations/` — AI-owned PostgreSQL schema.
- `docs/IMPLEMENTED_SERVICES.md` — detailed service, endpoint, and verification notes.

## Verification

The standard startup script runs dependency installation, linting, TypeScript checks, frontend tests, and a production build. Spring Boot verification additionally requires Java 21, Maven, and PostgreSQL.

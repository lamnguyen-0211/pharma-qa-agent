# Implemented Services

This document describes the services currently implemented in the Pharma Manager application. It reflects the repository as it exists today; planned infrastructure from the technology recommendation is listed separately as not yet implemented.

## Service map

```text
Browser
  |
  v
Next.js web app :3000
  |
  | POST /api/chat
  v
Spring Boot Core API :8080
  |
  | POST /v1/chat
  v
Python Pharma AI Service :8000
  |
  +--> AI PostgreSQL
       AI sessions, messages,
       providers, models, prompts
```

The browser never calls an LLM provider directly. The Next.js route is a thin gateway. Spring Boot owns users and business sessions, while Python owns all AI state and safety classification. The core service treats `chatSessionId` as opaque.

## 1. Next.js web application

Location: `src/frontend/`

Technology:

- Next.js App Router
- React
- TypeScript
- CSS Modules-style global stylesheet (`src/frontend/app/globals.css`)

Implemented behavior:

- Displays the Pharma Manager internal assistant landing screen.
- Creates a local-preview business session through `POST /api/business-sessions`.
- Accepts a user question after the business session is ready.
- Sends the question to the server route at `POST /api/chat`.
- Sends the core-owned `businessSessionId` and optional AI-owned `chatSessionId` with each request.
- Displays the returned answer.
- Shows a safety notice explaining that the preview is not a diagnostic or treatment system.
- Disables submission while a request is in progress or the question is empty.

Run locally:

```bash
npm ci
npm run dev
```

The web application starts on `http://localhost:3000`.

## 2. Spring Boot core API

Location: `src/backend/`

The core API owns users and business-session lifecycle. It validates `businessSessionId`, relays chat requests, and does not persist AI conversations, messages, prompts, providers, models, or audit events. Flyway owns only the core PostgreSQL schema migrations.

Endpoints:

- `GET /actuator/health`
- `POST /api/v1/users`
- `POST /api/v1/business-sessions`
- `GET /api/v1/business-sessions/{id}`
- `POST /api/v1/chat`

## 3. Next.js chat gateway

Location: `src/frontend/app/api/chat/route.ts`

Endpoint:

```http
POST /api/chat
Content-Type: application/json
```

Request:

```json
{
  "businessSessionId": "core-session-id",
  "chatSessionId": "optional-ai-session-id",
  "question": "What is this product used for?"
}
```

Validation:

- `question` is required.
- Leading and trailing whitespace is removed.
- Length must be between 1 and 4,000 characters.

The gateway forwards valid requests unchanged to:

```text
${CORE_API_URL}/api/v1/chat
```

The core validates the business session before forwarding. The AI service creates or reuses `chatSessionId` and returns it with the answer; core does not interpret or store it.

Error responses:

- `400` — invalid request payload.
- `503` — Python AI service unavailable.
- Backend response status — forwarded to the caller.

The gateway does not contain an OpenAI SDK, model prompt, API key, or model credentials.

## 4. Python Pharma AI service

Location: `src/ai-backend/`

Technology:

- Python
- FastAPI
- Pydantic
- LangGraph dependency reserved for the workflow implementation
- Uvicorn

Install and run:

```bash
cd src/ai-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The service starts on `http://localhost:8000`.

### Health endpoint

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "pharma-ai-agent"
}
```

### Chat endpoint

```http
POST /v1/chat
Content-Type: application/json
```

Request:

```json
{
  "question": "What is the dosage?"
}
```

Response:

```json
{
  "businessSessionId": "core-session-id",
  "chatSessionId": "ai-session-id",
  "answer": "...",
  "risk_level": "high",
  "citations": [],
  "trace_id": "..."
}
```

The AI service persists the user and assistant message pair atomically before returning. The `trace_id` is generated for each request as a correlation identifier.

## 4. Safety and policy workflow

Location: `src/ai-backend/app/workflow.py`

The current service uses one controlled orchestrator, not a multi-agent system.

Current flow:

```text
Question
  |
  v
Risk classification
  |-- emergency -> urgent-care response
  `-- low/high -> provider-not-configured response
```

Emergency patterns currently detected include:

- Chest pain
- Difficulty breathing
- Inability to breathe
- Overdose
- Severe allergic reaction language

High-risk patterns currently detected include:

- Dose or dosage questions
- Pregnancy-related questions
- Side effects
- Contraindications
- Adverse events

Emergency questions are stopped before any model provider call. The response advises contacting emergency services or a qualified healthcare professional.

## 5. Provider boundary

Location: `src/ai-backend/app/workflow.py`

`ModelProvider` defines the future provider contract:

```python
class ModelProvider:
    def complete(self, question: str) -> str:
        raise NotImplementedError
```

No production model provider is currently configured. The service fails closed with an explanatory response instead of inventing an answer.

The project intentionally does not implement an unofficial ChatGPT browser-session or OAuth-token exchange. A supported model provider and approved server-side authentication mechanism must be selected before enabling model responses.

## 6. Database ownership and local Docker infrastructure

Core Flyway creates `app_user` and `business_session` in `pharma_core`. The AI service applies `src/ai-backend/migrations/001_ai_schema.sql` to `pharma_ai`, creating `chat_session`, `chat_message`, `llm_provider`, `llm_model`, `prompt`, and `prompt_version`.

`docker-compose.yml` provides the local data services:

- `core-postgres` — PostgreSQL 16, database `pharma_core`, exposed on host port 5432 and used only by Spring Boot/Flyway.
- `ai-postgres` — PostgreSQL 16, database `pharma_ai`, exposed on host port 5433 and used only by FastAPI.
- `redis` — Redis 7 with AOF persistence, included for the cache layer in the recommended architecture. No current application code requires Redis yet.

Start only the data services with `docker compose up core-postgres ai-postgres redis`, or start the complete containerized stack with `docker compose up --build`. The databases use separate named volumes and Redis uses `redis_data`.

## 7. Verification services

Frontend verification is configured in the root `package.json`:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

Frontend tests cover chat validation, opaque session forwarding, and business-session bootstrap. Python API tests cover first-turn creation, subsequent-turn reuse, emergency handling, and the persistence-failure path.

Run Python tests after installing the AI-service requirements:

```bash
cd src/ai-backend
pytest -q
```

## Configuration

Copy the example environment file before running the web app:

```bash
cp .env.example .env.local
```

Current variables:

| Variable | Default | Purpose |
|---|---|---|
| `CORE_DATABASE_URL` | `jdbc:postgresql://127.0.0.1:5432/pharma_core` | Spring Boot core PostgreSQL connection |
| `AI_DATABASE_URL` | `postgresql://postgres:postgres@127.0.0.1:5433/pharma_ai` | FastAPI AI PostgreSQL connection |
| `AI_BACKEND_URL` | `http://127.0.0.1:8000` | URL of the Python AI service |

No OpenAI API key is currently read by the application.

## Not implemented yet

The following recommended services are not present in the current repository:

- Mobile client with React Native
- API gateway/WAF and rate limiting
- Authentication, consent, and role-based authorization for the Spring Boot core API
- Active LangGraph state graph and human-in-the-loop approvals
- LLM provider integration
- Approved-document ingestion and storage
- Hybrid keyword/vector retrieval
- Citation generation from source pages
- Redis cache and rate limiting
- Kafka, RabbitMQ, SQS, or another message queue
- OIDC, MFA, role-based access control, and consent management
- Secrets manager
- FHIR or enterprise integrations
- Docker deployment and Terraform infrastructure
- OpenTelemetry traces, metrics, centralized logs, and agent evaluation
- Durable tool-call records and production audit integrations

These are prerequisites for moving beyond the current development scaffold into a regulated production system.

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
  v
Controlled safety workflow
```

The browser never calls an LLM provider directly. The Next.js route is a thin gateway, while the Python service owns AI workflow decisions and safety classification.

## 1. Next.js web application

Location: `src/frontend/`

Technology:

- Next.js App Router
- React
- TypeScript
- CSS Modules-style global stylesheet (`src/frontend/app/globals.css`)

Implemented behavior:

- Displays the Pharma Manager internal assistant landing screen.
- Accepts a user question.
- Sends the question to the server route at `POST /api/chat`.
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

The core API owns conversation lifecycle, message persistence, and audit events. It delegates risk classification and AI responses to the Python service. Flyway owns the PostgreSQL schema migrations for this service.

Endpoints:

- `GET /actuator/health`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{id}`
- `POST /api/v1/conversations/{id}/messages`
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
  "question": "What is this product used for?"
}
```

Validation:

- `question` is required.
- Leading and trailing whitespace is removed.
- Length must be between 1 and 4,000 characters.

The gateway forwards valid requests to:

```text
${CORE_API_URL}/api/v1/chat
```

`AI_BACKEND_URL` defaults to `http://127.0.0.1:8000`.

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
  "answer": "...",
  "risk_level": "high",
  "citations": [],
  "trace_id": "..."
}
```

The `trace_id` is generated for each request so future audit and observability layers have a correlation identifier.

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

## 6. Prisma data layer

Location: `prisma/schema.prisma`

The current schema defines:

### Conversation

- `id`
- `createdAt`
- `updatedAt`
- Related messages

### Message

- `id`
- `conversationId`
- `role` (`USER`, `ASSISTANT`, or `SYSTEM`)
- `content`
- `riskLevel` (`LOW`, `MEDIUM`, `HIGH`, or `EMERGENCY`)
- `createdAt`

The schema uses PostgreSQL and includes an index on conversation and creation time. Database migrations, repository methods, persistence calls, and runtime database provisioning are not implemented yet.

Example environment variable:

```env
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/pharma_manager"
```

## 7. Verification services

Frontend verification is configured in the root `package.json`:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

Frontend tests currently cover request validation for the chat gateway. Python tests are in `src/ai-backend/tests/` and cover emergency and high-risk classification.

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
| `DATABASE_URL` | None | PostgreSQL connection string for the future Prisma persistence layer |
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

# Pharma Manager Core API

Spring Boot owns core users and business sessions. It validates a business session, relays the opaque chat request to the Python service, and does not persist AI conversations, messages, prompts, providers, models, or audit events.

## Run locally

Requirements: Java 21, Maven, and PostgreSQL.

```bash
createdb pharma_core
export CORE_DATABASE_URL='jdbc:postgresql://127.0.0.1:5432/pharma_core'
export DATABASE_USERNAME=postgres
export DATABASE_PASSWORD=postgres
export AI_BACKEND_URL='http://127.0.0.1:8000'
mvn spring-boot:run
```

The AI service uses its separate `AI_DATABASE_URL`, for example `postgresql://postgres:postgres@127.0.0.1:5433/pharma_ai`.

Flyway creates only the `app_user` and `business_session` tables on startup.

## API

```text
GET  /actuator/health
POST /api/v1/users
POST /api/v1/business-sessions
GET  /api/v1/business-sessions/{id}
POST /api/v1/chat
```

Create a local-preview user and business session before chatting:

```json
POST /api/v1/users
{ "externalSubject": "local-preview", "displayName": "Local Preview User" }

POST /api/v1/business-sessions
{ "userId": "<user-id>" }
```

`POST /api/v1/chat` accepts `{ "businessSessionId": "<core-id>", "chatSessionId": "<optional-ai-id>", "question": "..." }`. The core validates the business session, forwards the same JSON to Python `POST /v1/chat`, and returns the AI JSON unchanged. `chatSessionId` is created and persisted by the AI service; core treats it as opaque.

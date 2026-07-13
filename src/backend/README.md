# Pharma Manager Core API

Spring Boot owns business-facing conversation persistence and audit records. The Python service remains responsible for AI orchestration and safety classification.

## Run locally

Requirements: Java 21, Maven, and PostgreSQL.

```bash
createdb pharma_manager
export DATABASE_URL='jdbc:postgresql://127.0.0.1:5432/pharma_manager'
export DATABASE_USERNAME=postgres
export DATABASE_PASSWORD=postgres
export AI_BACKEND_URL='http://127.0.0.1:8000'
mvn spring-boot:run
```

Flyway creates the `conversation`, `message`, and `audit_event` tables on startup.

## API

```text
GET  /actuator/health
POST /api/v1/conversations
GET  /api/v1/conversations/{id}
POST /api/v1/conversations/{id}/messages
POST /api/v1/chat
```

`POST /api/v1/chat` accepts `{ "question": "..." }`, creates a conversation, records the user message, calls Python `POST /v1/chat`, records the assistant response and audit event, and returns the AI response plus `conversationId`.

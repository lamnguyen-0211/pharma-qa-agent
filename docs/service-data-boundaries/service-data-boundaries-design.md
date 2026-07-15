# Service Data Boundaries Design

## Goal

Separate core business persistence from AI persistence. Spring Boot owns users and business sessions; FastAPI owns all AI state and communicates with the core service through an opaque `chatSessionId`.

## Current problem

The Spring Boot service currently owns `conversation`, `message`, and `audit_event` tables and persists the user question and AI answer. The FastAPI service is stateless. The root Prisma schema also describes the same AI conversation data, making ownership ambiguous.

## Architecture

The application will use two PostgreSQL databases with separate service-owned migrations:

```text
Frontend
  |
  | businessSessionId, chatSessionId?, question
  v
Spring Boot Core API --------------> Core PostgreSQL
  |                                  app_user
  |                                  business_session
  |
  | opaque AI request/response relay
  v
FastAPI AI Backend ----------------> AI PostgreSQL
                                     chat_session
                                     chat_message
                                     llm_provider
                                     llm_model
                                     prompt
                                     prompt_version
```

The core service does not persist or interpret chat messages, prompt content, model configuration, risk records, citations, or AI audit events. It validates the core-owned business session, forwards the AI request, and returns the AI service response. The `chatSessionId` is an opaque correlation value and is not stored by the core service.

## Core database

Spring Boot will connect through `CORE_DATABASE_URL` and Flyway will create only:

- `app_user`: core application identity (`id`, `external_subject`, `display_name`, timestamps).
- `business_session`: application workflow context (`id`, `user_id`, `status`, timestamps).

The core API will expose business-session creation and retrieval. Its chat endpoint will accept `businessSessionId`, optional `chatSessionId`, and `question`. It will reject unknown business sessions, then relay the request to FastAPI without writing AI data.

## AI database

FastAPI will connect through `AI_DATABASE_URL` and initialize its own schema. The AI service will create or reuse `chat_session` based on the supplied opaque ID, then persist the user and assistant messages. It will also own tables for provider/model configuration and versioned prompt templates, even while no production model provider is configured.

The AI API request is:

```json
{
  "businessSessionId": "core-owned-id",
  "chatSessionId": "optional-ai-owned-id",
  "question": "..."
}
```

The response includes the AI-created or reused `chatSessionId`, the supplied `businessSessionId`, and the existing answer/risk/citation/trace fields.

## Failure handling

- Unknown `businessSessionId`: core returns `404` without contacting FastAPI.
- Missing or invalid question/session input: the relevant service returns `400`.
- Unavailable AI service or AI database: core returns `503` and does not create or mutate core business records beyond the already-existing business session.
- AI response persistence failure: FastAPI fails the request rather than returning an answer that is not recorded in AI history.

## Testing

- Spring Boot tests verify business-session persistence, unknown-session rejection, and relay request shape.
- FastAPI tests verify first-turn chat-session creation, subsequent-turn reuse, persistence of both message roles, and emergency safety behavior.
- An API-level FastAPI test exercises the HTTP route with a fake AI repository so the primary flow and persistence failure path are covered without requiring a developer PostgreSQL instance.
- Compose/configuration checks verify separate core and AI database URLs and service dependencies.

## Scope

This change does not add authentication, a real LLM provider, retrieval, or frontend conversation-history UI. The frontend will retain the opaque IDs needed for the new request contract.

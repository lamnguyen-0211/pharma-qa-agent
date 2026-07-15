# Service Data Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all AI persistence into a dedicated AI PostgreSQL database while making Spring Boot own only users/business sessions and relay chat requests through opaque session IDs.

**Architecture:** Spring Boot will use a core PostgreSQL database containing `app_user` and `business_session`. FastAPI will use a separate AI PostgreSQL database containing chat history, providers, models, and versioned prompts. Spring Boot validates `businessSessionId`, forwards `chatSessionId` and the question to FastAPI without persisting or interpreting AI state, and returns FastAPI’s response.

**Tech Stack:** Spring Boot 3.5.3, Java 21, JdbcTemplate, Flyway, PostgreSQL 16, FastAPI, Pydantic 2, psycopg 3, pytest, Next.js 14, TypeScript, Docker Compose.

## Global Constraints

- Core PostgreSQL must contain only core business tables; it must not contain conversation, message, audit, prompt, provider, or model tables.
- AI PostgreSQL owns `chat_session`, `chat_message`, `llm_provider`, `llm_model`, `prompt`, and `prompt_version`.
- `chatSessionId` is created and persisted by FastAPI; the core service treats it as opaque and never stores it.
- Chat requests contain `businessSessionId`, optional `chatSessionId`, and `question`.
- Chat responses contain both session IDs plus the AI answer/risk/citations/trace fields.
- No authentication, production model provider, retrieval, or chat-history UI is added in this feature.
- Preserve unrelated existing working-tree changes and only stage task-related files.

---

### Task 1: Replace core AI persistence with business-user/session persistence

**Files:**
- Modify: `src/backend/src/main/resources/db/migration/V1__create_core_tables.sql`
- Modify: `src/backend/src/main/resources/application.yml`
- Create: `src/backend/src/main/java/com/pharmamanager/core/business/UserRequest.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/business/UserResponse.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/business/BusinessSessionRequest.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/business/BusinessSessionResponse.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/business/BusinessSessionService.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/api/BusinessSessionController.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/api/BusinessSessionNotFoundException.java`
- Create: `src/backend/src/test/java/com/pharmamanager/core/business/BusinessSessionServiceTest.java`

**Interfaces:**
- `POST /api/v1/users` consumes `{ "externalSubject": string, "displayName": string }` and produces `UserResponse`.
- `POST /api/v1/business-sessions` consumes `{ "userId": string }` and produces `BusinessSessionResponse`.
- `GET /api/v1/business-sessions/{id}` produces `BusinessSessionResponse` or `404`.
- `BusinessSessionService.requireSession(String id)` returns `BusinessSessionResponse` or throws `BusinessSessionNotFoundException`.

- [x] **Step 1: Write the failing core persistence tests**

Add Mockito-based tests that assert `createUser` inserts into `app_user`, `createBusinessSession` inserts into `business_session`, `getBusinessSession` maps the row, and `requireSession` throws for `EmptyResultDataAccessException`.

```java
@Test
void requireSessionTranslatesMissingRowToDomainException() {
    when(jdbc.queryForObject(anyString(), any(RowMapper.class), eq("missing")))
        .thenThrow(new EmptyResultDataAccessException(1));

    assertThatThrownBy(() -> service.requireSession("missing"))
        .isInstanceOf(BusinessSessionNotFoundException.class);
}
```

- [x] **Step 2: Run the focused test and verify it fails**

Run: `cd src/backend && mvn -q -Dtest=BusinessSessionServiceTest test`

Expected: FAIL because the business package and service do not exist yet.

- [x] **Step 3: Replace the Flyway schema with core-owned tables**

Make `V1__create_core_tables.sql` create only these tables and indexes:

```sql
CREATE TABLE app_user (
  id VARCHAR(36) PRIMARY KEY,
  external_subject VARCHAR(255) NOT NULL UNIQUE,
  display_name VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE business_session (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL REFERENCES app_user(id),
  status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX business_session_user_created_idx ON business_session (user_id, created_at);
```

- [x] **Step 4: Implement JdbcTemplate business services and endpoints**

Use UUID strings for IDs and `OffsetDateTime.now()` for inserts. `createUser` inserts the two caller-provided fields; `createBusinessSession` verifies the user exists before inserting; `getBusinessSession` maps the row. Add `@Valid` controller methods for the three endpoints.

- [x] **Step 5: Map missing business sessions to HTTP 404**

Update `ApiExceptionHandler` to handle `BusinessSessionNotFoundException` with `ErrorResponse("Business session not found.")`, while leaving AI dependency failures as `503`.

- [x] **Step 6: Run the focused test and verify it passes when Java 21/Maven are available**

Run: `cd src/backend && mvn -q -Dtest=BusinessSessionServiceTest test`

Expected: PASS.

---

### Task 2: Make Spring Boot a chat relay with no AI data model

**Files:**
- Modify: `src/backend/src/main/java/com/pharmamanager/core/api/ChatRequest.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/api/ChatRelayController.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/chat/ChatRelayService.java`
- Modify: `src/backend/src/main/java/com/pharmamanager/core/ai/AiClient.java`
- Delete: `src/backend/src/main/java/com/pharmamanager/core/api/ConversationController.java`
- Delete: `src/backend/src/main/java/com/pharmamanager/core/api/ConversationResponse.java`
- Delete: `src/backend/src/main/java/com/pharmamanager/core/api/ChatResponse.java`
- Delete: `src/backend/src/main/java/com/pharmamanager/core/conversation/ConversationService.java`
- Create: `src/backend/src/test/java/com/pharmamanager/core/api/ApiExceptionHandlerTest.java`
- Create: `src/backend/src/test/java/com/pharmamanager/core/chat/ChatRelayServiceTest.java`

**Interfaces:**
- `ChatRequest` has `businessSessionId`, nullable `chatSessionId`, and a required 1–4,000 character `question`.
- `AiClient.chat(ChatRequest request)` POSTs the same JSON to FastAPI `/v1/chat` and returns the response body as an opaque Jackson `JsonNode`.
- `ChatRelayService.chat(ChatRequest request)` first calls `BusinessSessionService.requireSession`, then calls `AiClient.chat`; it performs no AI persistence, risk mapping, citation processing, or response transformation.
- `POST /api/v1/chat` returns the opaque AI JSON with HTTP 200.

- [x] **Step 1: Write relay tests before changing implementation**

Mock `BusinessSessionService` and `AiClient`. Assert a valid request calls `requireSession` and forwards the exact `businessSessionId`, `chatSessionId`, and question. Assert an unknown business session never calls `AiClient`.

```java
@Test
void validChatRequestIsForwardedWithoutCorePersistence() {
    var request = new ChatRequest("business-1", "chat-1", "What is this used for?");
    var aiResponse = objectMapper.readTree("{\"chatSessionId\":\"chat-1\",\"answer\":\"ok\"}");
    when(aiClient.chat(request)).thenReturn(aiResponse);

    assertThat(service.chat(request)).isEqualTo(aiResponse);
    verify(businessSessions).requireSession("business-1");
    verify(aiClient).chat(request);
    verifyNoMoreInteractions(businessSessions, aiClient);
}
```

- [x] **Step 2: Run the relay test and verify it fails**

Run: `cd src/backend && mvn -q -Dtest=ChatRelayServiceTest test`

Expected: FAIL because the relay service and request contract do not exist.

- [x] **Step 3: Implement the new request and opaque relay**

Use a Java record for `ChatRequest` with `@NotBlank`/`@Size` on `question` and `@NotBlank` on `businessSessionId`. Keep `chatSessionId` nullable. Configure `AiClient` to post this request to `/v1/chat` and deserialize only to `JsonNode`; do not retain `AiResult`, `ChatResponse`, or any conversation service.

- [x] **Step 4: Add the relay controller and remove conversation routes**

Create `ChatRelayController` at `/api/v1/chat`. Delete the three conversation endpoints and the service that inserts `message` and `audit_event` rows. The only core chat route must be `POST /api/v1/chat`.

- [x] **Step 5: Run backend relay tests when Java 21/Maven are available**

Run: `cd src/backend && mvn -q -Dtest=BusinessSessionServiceTest,ChatRelayServiceTest test`

Expected: PASS, with no references to `conversation`, `message`, or `audit_event` in Java source.

---

### Task 3: Add AI-owned persistence for sessions, messages, providers, models, and prompts

**Files:**
- Modify: `src/ai-backend/requirements.txt`
- Create: `src/ai-backend/migrations/001_ai_schema.sql`
- Create: `src/ai-backend/app/store.py`
- Modify: `src/ai-backend/app/models.py`
- Modify: `src/ai-backend/app/workflow.py`
- Modify: `src/ai-backend/app/main.py`
- Modify: `src/ai-backend/tests/test_workflow.py`
- Create: `src/ai-backend/tests/test_api.py`

**Interfaces:**
- `AiStore.record_turn(chat_session_id: str | None, business_session_id: str, question: str, response: ChatResponse) -> str` returns the AI-owned session ID and atomically inserts the session/user/assistant records.
- `PostgresAiStore(database_url: str)` reads `migrations/001_ai_schema.sql` on startup and uses `psycopg.connect` for transactions.
- `PharmaAgent(store: AiStore)` classifies and creates the deterministic response, then delegates atomic turn persistence to the store.
- FastAPI `POST /v1/chat` accepts and returns camelCase `businessSessionId`/`chatSessionId` fields.

- [x] **Step 1: Add the database dependency and schema**

Add `psycopg[binary]==3.2.9` to `requirements.txt`. Create SQL tables with UUID IDs and timestamp columns:

```sql
CREATE TABLE IF NOT EXISTS chat_session (
  id UUID PRIMARY KEY,
  business_session_id VARCHAR(36) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chat_message (
  id UUID PRIMARY KEY,
  chat_session_id UUID NOT NULL REFERENCES chat_session(id) ON DELETE CASCADE,
  role VARCHAR(16) NOT NULL CHECK (role IN ('USER', 'ASSISTANT', 'SYSTEM')),
  content TEXT NOT NULL,
  risk_level VARCHAR(16) NOT NULL DEFAULT 'LOW',
  trace_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS llm_provider (
  id UUID PRIMARY KEY,
  name VARCHAR(128) NOT NULL UNIQUE,
  provider_type VARCHAR(64) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS llm_model (
  id UUID PRIMARY KEY,
  provider_id UUID NOT NULL REFERENCES llm_provider(id) ON DELETE CASCADE,
  name VARCHAR(128) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(provider_id, name)
);
CREATE TABLE IF NOT EXISTS prompt (
  id UUID PRIMARY KEY,
  name VARCHAR(128) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS prompt_version (
  id UUID PRIMARY KEY,
  prompt_id UUID NOT NULL REFERENCES prompt(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  template TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(prompt_id, version)
);
CREATE INDEX IF NOT EXISTS chat_message_session_created_idx ON chat_message(chat_session_id, created_at);
```

- [x] **Step 2: Write failing AI persistence/API tests**

Create a fake store that records turns in memory. Test two HTTP calls: the first returns a newly created `chatSessionId` and stores USER/ASSISTANT messages; the second uses the returned ID and stores two additional messages under the same session. Add a fake-store failure test asserting HTTP 503 and an emergency test asserting the urgent-care response is still classified as `emergency`.

```python
def test_chat_creates_then_reuses_ai_session(client):
    first = client.post("/v1/chat", json={"businessSessionId": "business-1", "question": "What is this?"})
    second = client.post("/v1/chat", json={
        "businessSessionId": "business-1",
        "chatSessionId": first.json()["chatSessionId"],
        "question": "Can I take a dose?",
    })

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["chatSessionId"] == first.json()["chatSessionId"]
    assert fake_store.roles_for(first.json()["chatSessionId"]) == ["USER", "ASSISTANT", "USER", "ASSISTANT"]
```

- [x] **Step 3: Run the AI tests and verify they fail**

Run: `cd src/ai-backend && python -m pytest -q`

Expected: FAIL because the store injection, session fields, and API factory do not exist.

- [x] **Step 4: Implement Pydantic request/response aliases and store**

Use Pydantic `Field(alias="businessSessionId")` and `Field(alias="chatSessionId")` with `ConfigDict(populate_by_name=True)`. Implement `PostgresAiStore.record_turn` as one transaction: create the session when the ID is absent, lock/check an existing session and its `business_session_id` when present, insert USER and ASSISTANT rows, update `updated_at`, and commit. Raise a domain persistence exception on database errors.

- [x] **Step 5: Inject the store into the agent and FastAPI app factory**

Add `create_app(agent: PharmaAgent | None = None)` so tests can pass a fake store. The production app constructs `PostgresAiStore(os.environ["AI_DATABASE_URL"])`, initializes the schema during startup, and passes it to `PharmaAgent`. Map domain persistence errors to HTTP 503. Keep the deterministic provider-not-configured response and emergency gate.

- [x] **Step 6: Run the AI tests and verify they pass**

Run: `cd src/ai-backend && python -m pytest -q`

Expected: PASS for workflow classification, API session creation/reuse, message persistence behavior, emergency handling, and persistence failure handling.

---

### Task 4: Split local infrastructure and remove the obsolete Prisma AI schema

**Files:**
- Modify: `docker-compose.yml`
- Modify: `Dockerfile`
- Modify: `.env.example`
- Delete: `prisma/schema.prisma`
- Modify: `package.json`
- Modify: `package-lock.json`
- Modify: `src/backend/src/main/resources/application.yml`
- Modify: `src/ai-backend/README.md`
- Modify: `src/backend/README.md`

**Interfaces:**
- Core container receives `CORE_DATABASE_URL=jdbc:postgresql://core-postgres:5432/pharma_core`.
- AI container receives `AI_DATABASE_URL=postgresql://postgres:postgres@ai-postgres:5432/pharma_ai`.
- `core-api` depends on `core-postgres` and `ai-backend`; `ai-backend` depends on `ai-postgres`.

- [x] **Step 1: Add two PostgreSQL services and health checks**

Replace the shared `postgres` service with `core-postgres` (`POSTGRES_DB=pharma_core`, host port 5432, `core_postgres_data` volume) and `ai-postgres` (`POSTGRES_DB=pharma_ai`, host port 5433, `ai_postgres_data` volume). Give each a `pg_isready` health check and keep Redis unchanged.

- [x] **Step 2: Wire isolated database URLs into containers**

Set the core API’s Spring datasource to `CORE_DATABASE_URL` and the AI backend’s `AI_DATABASE_URL`. Add the AI database health dependency and copy `src/ai-backend/migrations` into the AI image at `/app/migrations`.

- [x] **Step 3: Remove the root Prisma AI model**

Remove the unused Prisma schema, `@prisma/client`, `prisma`, and `prisma:generate` script from the root package. Confirm no frontend source imports Prisma and no root `DATABASE_URL` remains documented.

- [x] **Step 4: Update local run documentation**

Document separate `CORE_DATABASE_URL` and `AI_DATABASE_URL` values, both database service names/ports, and the new API contracts in the two service READMEs. Do not describe Spring Boot as owning conversation/message/audit persistence.

- [x] **Step 5: Verify Compose configuration**

Run: `docker compose config --quiet`

Expected: PASS, with both database services, isolated environment variables, and valid service dependencies present.

---

### Task 5: Update the frontend gateway and browser session flow

**Files:**
- Modify: `src/frontend/app/api/chat/route.ts`
- Modify: `src/frontend/app/api/chat/route.test.ts`
- Create: `src/frontend/app/api/business-sessions/route.ts`
- Create: `src/frontend/app/api/business-sessions/route.test.ts`
- Modify: `src/frontend/app/page.tsx`
- Modify: `src/frontend/lib/ai.ts`

**Interfaces:**
- `POST /api/business-sessions` creates a local-preview core user/session and returns `{ businessSessionId: string }`.
- `POST /api/chat` consumes `{ businessSessionId, chatSessionId?, question }` and forwards the exact payload to core.
- Browser state stores `businessSessionId` and the returned AI-owned `chatSessionId`; it never stores chat messages locally.

- [x] **Step 1: Write failing gateway tests**

Test that `/api/chat` rejects a missing business session with 400, forwards both session IDs and the question to `CORE_API_URL`, and returns the AI response unchanged. Test `/api/business-sessions` forwards the preview user payload to the core endpoint.

- [x] **Step 2: Run frontend tests and verify the new tests fail**

Run: `npm test -- --runInBand`

Expected: FAIL only for the new session-contract tests.

- [x] **Step 3: Implement the route contracts**

Update the Zod schema and forwarding body in `route.ts`. Add the session bootstrap route that calls `POST /api/v1/business-sessions` with a local-preview user identity. Update `AssistantResponse` to include `businessSessionId` and `chatSessionId`.

- [x] **Step 4: Persist opaque IDs in the page state**

On mount, create one business session. Disable chat submission until it exists. Include both IDs in each request and set `chatSessionId` from each successful response.

- [x] **Step 5: Run frontend verification**

Run: `npm test -- --runInBand && npm run lint && npm run typecheck && npm run build`

Expected: PASS.

---

### Task 6: Add end-to-end verification and update project state/documentation

**Files:**
- Modify: `init.sh`
- Modify: `README.md`
- Modify: `docs/IMPLEMENTED_SERVICES.md`
- Modify: `feature_list.json`
- Modify: `progress.md`
- Modify: `session-handoff.md`

**Interfaces:**
- `./init.sh` runs frontend checks, AI pytest checks, and Spring Boot Maven checks when their toolchains are available.
- The documented primary flow is: create core business session → send first chat without `chatSessionId` → receive AI `chatSessionId` → send second chat with that ID.

- [x] **Step 1: Add the AI API E2E command to startup verification**

Run `python -m pytest -q` from `src/ai-backend` when Python and its dependencies are available. Keep the existing fail-fast behavior for missing Java/Maven and ensure the standard path reports the exact unavailable tool.

- [x] **Step 2: Update architecture and endpoint documentation**

Replace statements that Spring Boot owns conversations/messages/audits with the split ownership model. Document core tables, AI tables, separate database URLs, request/response examples, and the fact that `chatSessionId` is AI-owned and opaque to core.

- [x] **Step 3: Update feature state and handoff evidence**

Mark the service-boundary feature evidence in `feature_list.json` and `progress.md` with the exact commands run, including any Java/Maven/PostgreSQL environment blocker. Update `session-handoff.md` with the new database services, branch, and remaining risks.

- [x] **Step 4: Run complete verification; Spring Boot remains blocked by missing Java 21**

Run:

```bash
./init.sh
cd src/ai-backend && python -m pytest -q
docker compose config --quiet
git diff --check
```

Expected: frontend and AI checks pass; Spring Boot either passes or reports the known missing toolchain; Compose and whitespace checks pass.

- [ ] **Step 5: Review, stage, and commit only task files**

Run `git diff --stat`, `git diff`, and `git status --short`. Confirm unrelated pre-existing changes are not included. Confirm the branch with `git branch --show-current`, then stage the task files and commit with:

```bash
git add AGENTS.md docs/service-data-boundaries src/backend src/ai-backend docker-compose.yml Dockerfile .env.example package.json package-lock.json README.md docs/IMPLEMENTED_SERVICES.md init.sh feature_list.json progress.md session-handoff.md
git commit -m "refactor: isolate AI and core persistence"
```

- [ ] **Step 6: Push and verify**

Run:

```bash
git push -u origin "$(git branch --show-current)"
git rev-parse HEAD
```

Expected: the current branch and commit hash are reported. If the repository’s read-only Git metadata or authentication prevents commit/push, preserve the working tree and report the exact command output.

# Task 2 Chat Relay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Spring Boot chat endpoint validate a core-owned business session and otherwise relay the FastAPI payload and JSON response without owning AI data.

**Architecture:** `ChatRelayController` receives the new session-aware request contract and delegates to `ChatRelayService`. The service verifies `businessSessionId` through `BusinessSessionService` before delegating the unchanged record to `AiClient`, which returns an opaque `JsonNode`; no JDBC, response mapping, or AI persistence is permitted in the relay path.

**Tech Stack:** Spring Boot 3.5.3, Java 21, Jakarta Validation, Jackson `JsonNode`, RestClient, JUnit 5, Mockito, AssertJ.

## Global Constraints

- Preserve all existing Task 1 working-tree edits and stage only Task 2 files.
- The sole core chat route is `POST /api/v1/chat`.
- `ChatRequest` contains nonblank `businessSessionId`, nullable `chatSessionId`, and a nonblank 1–4,000-character `question`.
- FastAPI response JSON is opaque to Spring Boot and must be returned unchanged.
- Core Java source must contain no conversation, message, or audit-event persistence references after this task.

---

### Task 1: Establish relay behavior with focused tests

**Files:**
- Create: `src/backend/src/test/java/com/pharmamanager/core/chat/ChatRelayServiceTest.java`
- Create: `src/backend/src/test/java/com/pharmamanager/core/api/ApiExceptionHandlerTest.java`

**Interfaces:**
- Consumes: `BusinessSessionService.requireSession(String)` and `AiClient.chat(ChatRequest)`.
- Produces: test-proven `ChatRelayService.chat(ChatRequest): JsonNode` behavior and 404 error mapping for unknown business sessions.

- [ ] **Step 1: Write the failing relay tests**

Create Mockito tests with a `ChatRequest("business-1", "chat-1", "What is this used for?")`, stubbing `aiClient.chat(request)` to return `objectMapper.readTree("{\"chatSessionId\":\"chat-1\",\"answer\":\"ok\"}")`. Assert the returned node is identical, verify `requireSession("business-1")` occurs before the exact request is forwarded, and assert `BusinessSessionNotFoundException` prevents an AI call. Add a direct exception-handler test for `ErrorResponse("Business session not found.")`.

- [ ] **Step 2: Verify red**

Run: `cd src/backend && mvn -q -Dtest=ChatRelayServiceTest,ApiExceptionHandlerTest test`

Expected: compilation failure because `ChatRelayService` and `AiClient.chat` do not exist and the request constructor has the old shape.

### Task 2: Implement the opaque relay and remove legacy state

**Files:**
- Modify: `src/backend/src/main/java/com/pharmamanager/core/api/ChatRequest.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/api/ChatRelayController.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/chat/ChatRelayService.java`
- Modify: `src/backend/src/main/java/com/pharmamanager/core/ai/AiClient.java`
- Delete: `src/backend/src/main/java/com/pharmamanager/core/api/ConversationController.java`
- Delete: `src/backend/src/main/java/com/pharmamanager/core/api/ConversationResponse.java`
- Delete: `src/backend/src/main/java/com/pharmamanager/core/api/ChatResponse.java`
- Delete: `src/backend/src/main/java/com/pharmamanager/core/conversation/ConversationService.java`

**Interfaces:**
- Produces `POST /api/v1/chat` returning HTTP 200 with the AI `JsonNode`.

- [ ] **Step 1: Implement the request record**

Define `public record ChatRequest(@NotBlank String businessSessionId, String chatSessionId, @NotBlank @Size(max = 4000) String question) {}` so Jackson retains the FastAPI camel-case JSON property names and `chatSessionId` remains nullable.

- [ ] **Step 2: Implement client and service**

Make `AiClient.chat` call `POST /v1/chat`, set JSON content type, send the `ChatRequest` unchanged, and deserialize to `JsonNode`, throwing the existing unavailable-dependency exception when the body is absent. Implement `ChatRelayService.chat` as exactly `businessSessions.requireSession(request.businessSessionId()); return aiClient.chat(request);`.

- [ ] **Step 3: Replace routes and delete persistence code**

Create the validated `ChatRelayController` at `/api/v1/chat`; delete all three conversation routes, both legacy response records, and `ConversationService`, which is the only Java code inserting `message` or `audit_event` rows.

- [ ] **Step 4: Verify green and boundary scan**

Run: `cd src/backend && mvn -q -Dtest=BusinessSessionServiceTest,ChatRelayServiceTest,ApiExceptionHandlerTest test`

Run: `rg -n -i 'conversation|message|audit_event' src/backend/src/main/java`

Expected: focused tests pass and the source scan produces no matches.

### Task 3: Review, record, and commit the scoped work

**Files:**
- Create: `.superpowers/sdd/task-2-report.md`

- [ ] **Step 1: Review scoped diff and workspace state**

Run `git diff --check -- <Task 2 paths>`, `git diff -- <Task 2 paths>`, and `git branch --show-current`; ensure Task 1 files remain unstaged.

- [ ] **Step 2: Record verification evidence**

Write `.superpowers/sdd/task-2-report.md` with changed/deleted files, relay contract, focused-test results or environment blocker, scan result, commit/push result, and risks.

- [ ] **Step 3: Attempt scoped commit**

Stage only the Task 2 files and report with `git add -- <Task 2 paths>`; run `git commit -m "fix: relay chat without core AI persistence"` only on a named branch. Attempt `git push -u origin "$(git branch --show-current)"` after a successful commit and record the exact outcome.

## Self-Review

- All brief requirements map to Task 1 or Task 2 above: contract, opaque forwarding, session validation, error behavior, route deletion, source boundary scan, and focused tests.
- No placeholders or alternate response mapping are included.
- The request, client, service, and controller signatures use the same `ChatRequest` and `JsonNode` types throughout.

# feat-006 Authenticated, Consent-Aware Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add locally runnable Keycloak OIDC authentication plus server-enforced consent, identity ownership, and role boundaries.

**Architecture:** Auth.js maintains the Next.js server session with Keycloak. Next.js gateways attach the server-held access token to Spring Boot requests. Spring Security validates JWTs and core services upsert the subject, enforce consent, scope sessions, and authorize knowledge operations.

**Tech Stack:** Next.js 14, Auth.js/NextAuth v4, Keycloak, Spring Boot 3.5, Spring Security OAuth2 Resource Server, PostgreSQL/Flyway, TypeScript, Jest, Playwright, Docker Compose.

## Global Constraints

- Use Keycloak as the local OIDC provider; do not add a development-only fake identity path.
- Keep provider credentials and access tokens server-side.
- Use the OIDC `sub` claim as the stable identity key.
- Return `401` for unauthenticated, `403` for insufficient role, and `428` with `CONSENT_REQUIRED` for missing application consent.
- Scope every business-session operation to the authenticated subject.
- Do not add authentication or authorization logic to the Python AI service in this feature.

---

### Task 1: Add Keycloak local realm and environment contract

**Files:**
- Create: `infra/keycloak/realm-export.json`
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `README.md`

- [ ] Add a Keycloak service on host port `8081`, import the `pharma-manager` realm, define `PHARMA_USER` and `PHARMA_ADMIN`, and create local test users without production secrets.
- [ ] Add `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `NEXTAUTH_SECRET`, and `CONSENT_VERSION` examples.
- [ ] Document `docker compose up keycloak` and local test credentials.
- [ ] Run `docker compose config --quiet` and verify the realm JSON parses.

### Task 2: Configure Spring JWT validation and identity mapping

**Files:**
- Modify: `src/backend/pom.xml`
- Create: `src/backend/src/main/java/com/pharmamanager/core/security/SecurityConfig.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/security/KeycloakJwtAuthenticationConverter.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/security/AuthenticatedIdentity.java`
- Modify: `src/backend/src/main/resources/application.yml`
- Modify: `src/backend/src/test/java/com/pharmamanager/core/security/*`

- [ ] Add Spring Security and OAuth2 resource-server dependencies.
- [ ] Configure issuer-based JWT validation, stateless sessions, public health access, and authenticated `/api/v1/**` access.
- [ ] Convert Keycloak realm roles into `ROLE_PHARMA_USER` and `ROLE_PHARMA_ADMIN` authorities.
- [ ] Expose a small identity adapter that reads `sub` and display-name claims without accepting client-supplied identity fields.
- [ ] Test valid claims, missing subject, wrong issuer behavior, role mapping, and unauthenticated API responses.

### Task 3: Add consent persistence and authenticated profile endpoints

**Files:**
- Create: `src/backend/src/main/resources/db/migration/V2__create_user_consent.sql`
- Create: `src/backend/src/main/java/com/pharmamanager/core/consent/ConsentService.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/consent/ConsentResponse.java`
- Create: `src/backend/src/main/java/com/pharmamanager/core/api/MeController.java`
- Modify: `src/backend/src/main/java/com/pharmamanager/core/business/BusinessSessionService.java`
- Modify: `src/backend/src/main/java/com/pharmamanager/core/api/ApiExceptionHandler.java`
- Modify: `src/backend/src/test/java/com/pharmamanager/core/consent/*`

- [ ] Add `user_consent(user_id, consent_version, accepted_at, accepted_subject)` with a primary key on user/version and a foreign key to `app_user`.
- [ ] Add `GET /api/v1/me` and `POST /api/v1/me/consent`; derive the user from the JWT and upsert identity server-side.
- [ ] Add `ConsentRequiredException` and stable `{ "error": "CONSENT_REQUIRED", "consentVersion": "..." }` handling with status 428.
- [ ] Test first-time profile, exact-version acceptance, repeat acceptance, and stale-version rejection.

### Task 4: Enforce ownership and role boundaries in core APIs

**Files:**
- Modify: `src/backend/src/main/java/com/pharmamanager/core/api/BusinessSessionController.java`
- Modify: `src/backend/src/main/java/com/pharmamanager/core/business/BusinessSessionService.java`
- Modify: `src/backend/src/main/java/com/pharmamanager/core/chat/ChatRelayService.java`
- Modify: `src/backend/src/main/java/com/pharmamanager/core/api/KnowledgeDocumentController.java`
- Modify: `src/backend/src/main/java/com/pharmamanager/core/knowledge/KnowledgeRelayService.java`
- Modify: `src/backend/src/test/java/com/pharmamanager/core/business/BusinessSessionServiceTest.java`
- Modify: `src/backend/src/test/java/com/pharmamanager/core/chat/ChatRelayServiceTest.java`
- Modify: `src/backend/src/test/java/com/pharmamanager/core/api/KnowledgeDocumentControllerTest.java`

- [ ] Replace client-provided `externalSubject` bootstrap with the authenticated identity.
- [ ] Require accepted consent before creating sessions or relaying chat.
- [ ] Add an owner predicate to session lookup and chat relay; return 404 for another user’s ID.
- [ ] Require `PHARMA_USER` or `PHARMA_ADMIN` for chat and `PHARMA_ADMIN` for document list/upload.
- [ ] Test cross-user access, no-consent access, user role denial, admin success, and that AI is not called on rejected requests.

### Task 5: Wire Auth.js and authenticated Next.js gateways

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Create: `src/frontend/auth.ts`
- Create: `src/frontend/app/api/auth/[...nextauth]/route.ts`
- Create: `src/frontend/lib/server-auth.ts`
- Modify: `src/frontend/app/api/business-sessions/route.ts`
- Modify: `src/frontend/app/api/chat/route.ts`
- Modify: `src/frontend/app/api/knowledge/documents/route.ts`
- Create: `src/frontend/app/api/me/route.ts`
- Create/modify: corresponding Jest tests

- [ ] Add NextAuth v4 and the Keycloak provider; persist the access token in the encrypted server session and expose only safe profile fields to the client session.
- [ ] Add a shared server helper that returns a bearer token or a 401 response.
- [ ] Forward `Authorization` to Spring Boot on every gateway request and remove the hardcoded local-preview body.
- [ ] Add profile gateway tests for 401, consent-required, and successful responses.

### Task 6: Add login, consent, and forbidden UI states

**Files:**
- Create: `src/frontend/app/components/AuthControls.tsx`
- Create: `src/frontend/app/components/ConsentGate.tsx`
- Modify: `src/frontend/app/page.tsx`
- Modify: `src/frontend/app/knowledge/page.tsx`
- Modify: `src/frontend/app/layout.tsx`
- Modify: `src/frontend/app/globals.css`
- Modify: page/component Jest tests

- [ ] Add sign-in/sign-out controls using Auth.js client helpers.
- [ ] Load `/api/me`; render consent acceptance before session bootstrap; render a clear forbidden state for non-admin knowledge users.
- [ ] Preserve existing chat, citations, upload metadata, retry, and error behavior after the gate is satisfied.
- [ ] Test anonymous, consent-required, consent-accepted, and forbidden UI branches.

### Task 7: Add authenticated browser coverage and verification evidence

**Files:**
- Modify: `playwright.config.ts`
- Create: `e2e/feat-006-oidc.spec.ts`
- Modify: `feature_list.json`
- Modify: `progress.md`
- Modify: `docs/IMPLEMENTED_SERVICES.md`

- [ ] Add an optional Docker-backed Playwright project that logs into local Keycloak, accepts consent, starts a session, and chats.
- [ ] Cover the important failure path where a normal user reaches knowledge access and receives a forbidden result.
- [ ] Run `npm ci`, lint, typecheck, Jest, Playwright, build, Python tests, Compose validation, and the Java 21 builder tests.
- [ ] Run `graphify update .`, review `git diff`, record evidence, and update feat-006 only after all required checks pass.

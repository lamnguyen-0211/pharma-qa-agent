# feat-006 Authenticated, Consent-Aware Workspace Design

## Goal

Replace the hardcoded `local-preview` identity with a real, locally testable OIDC flow and enforce consent and role boundaries for core sessions, chat, and approved-document operations.

## Recommended approach

Use Keycloak in Docker Compose as the local OIDC provider, Auth.js v4 with the Keycloak provider in Next.js for the browser session, and Spring Security OAuth2 Resource Server for API token validation. The frontend never receives or forwards provider secrets; Next.js server routes obtain the access token from the Auth.js server session and send it to Spring Boot as a bearer token.

The browser flow is:

```text
Browser -> Next.js/Auth.js -> Keycloak login
Browser <- HttpOnly Auth.js session cookie
Next.js route -> Spring Boot (Bearer access token)
Spring Boot -> issuer discovery/JWKS, app_user, consent, role checks
```

## Identity and authorization contract

- Keycloak realm: `pharma-manager`; local client: `pharma-frontend`.
- OIDC issuer is configurable with `OIDC_ISSUER`; local default is `http://127.0.0.1:8081/realms/pharma-manager`.
- The access token `sub` is the stable external subject. Spring rejects missing, invalid, expired, or wrong-issuer tokens with `401`.
- Keycloak realm roles are `PHARMA_USER` and `PHARMA_ADMIN`. Spring maps them to authorities with the `ROLE_` prefix.
- `app_user.external_subject` is upserted from the validated token; display name comes from `preferred_username`, `name`, or `email`.
- Every business session query and mutation is constrained by the authenticated user subject. A valid user cannot read, chat through, or mutate another user’s session.
- Knowledge list/upload requires `PHARMA_ADMIN`; chat requires `PHARMA_USER` or `PHARMA_ADMIN`.

## Consent contract

Add a core-owned `user_consent` table keyed by user and consent version. The active version is configured as `CONSENT_VERSION` with a deterministic local default. The API exposes:

- `GET /api/v1/me` — authenticated user profile, roles, and `consentAccepted` for the active version.
- `POST /api/v1/me/consent` — records acceptance of the exact active version and returns the updated profile.

Business-session creation and chat return `428 PRECONDITION_REQUIRED` with `CONSENT_REQUIRED` until the active version is accepted. Consent acceptance is explicit and auditable with timestamp and subject; no token claim is treated as application consent.

## Frontend behavior

- Auth.js exposes `/api/auth/signin`, `/api/auth/signout`, and `/api/auth/session`.
- The home and knowledge pages load the authenticated profile. Anonymous users see a sign-in action; signed-in users without consent see a consent panel; authorized users can use the existing workspace.
- The business-session route and chat/knowledge gateways require an Auth.js session and forward its access token to Spring Boot.
- The UI shows a concise forbidden state for insufficient role and a consent action for `428` responses.
- Existing chat and knowledge behavior remains unchanged after authentication and consent are satisfied.

## Failure handling

- Missing Auth.js session: frontend gateways return `401`.
- Invalid or missing bearer token at Spring: `401`.
- Authenticated user without required role: `403`.
- Authenticated user without current consent: `428` and a stable JSON error code.
- Session not owned by the authenticated user: `404` to avoid leaking another user’s session existence.
- Keycloak unavailable during login: Auth.js displays its normal sign-in error; API validation fails closed because issuer/JWKS validation cannot succeed.

## Testing and local operation

- Export a minimal Keycloak realm with the client, roles, and test users (`admin@example.test` and `user@example.test`). Credentials are local-development-only and documented as such.
- Add Spring unit tests for JWT claim mapping, consent service, ownership checks, and role-protected controllers.
- Add Next/Jest tests for bearer forwarding, anonymous/consent responses, and profile handling.
- Add Playwright coverage for Keycloak login, consent acceptance, authorized chat, and a normal-user rejection of knowledge upload.
- Keep live Keycloak/PostgreSQL E2E optional in the standard harness when Docker or browser dependencies are unavailable; deterministic gateway and backend tests remain required.

## Scope boundaries

This feature does not add production identity-provider operations, MFA policy, enterprise directory synchronization, refresh-token persistence, or authorization enforcement inside the Python service. Spring Boot is the authorization boundary for current business and knowledge operations; future AI document retrieval receives only already-authorized requests.

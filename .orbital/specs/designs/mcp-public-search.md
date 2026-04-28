---
abstract: Public MCP search surface for token-backed programmatic access to the knowledge graph.
out_of_scope: Browser web sessions, private FastAPI route ownership, non-search MCP tools, and Logto tenant provisioning runbooks.
---

# Design: mcp-public-search

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the first public Model Context Protocol surface for external model clients that need search access to the knowledge graph through user-created Logto personal access tokens.
- **Scope/Boundaries:** Covers the `apps/mcp` service boundary, MCP transport endpoint, `search` tool contract, Logto personal-access-token exchange, access-token validation, quota and usage attribution, internal usage-summary reads, private search API consumption, deployment exposure, and first-version validation expectations. Excludes browser session flows, browser-facing Dashboard endpoint ownership, self-service Logto Console provisioning details, additional MCP tools, and backend ranking changes.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Public programmatic access must use an explicitly designated public surface, private FastAPI routes must remain internal service interfaces, repository-owned internal API calls must stay contract-driven, module boundaries must remain explicit, runtime behavior must be reproducible, and active specs must stay synchronized with behavior-changing public access decisions.
- **Detail Commitments:** `apps/mcp` is a dedicated Python MCP service. It exposes one remote Streamable HTTP MCP endpoint and one model-callable tool named `search`. MCP clients authenticate by sending a user-created Logto personal access token as a bearer credential. The service exchanges that PAT with Logto for a short-lived access token, validates the resulting token's issuer, audience, scope, and user subject, derives quota identity from both the user subject and PAT fingerprint, records usage events, exposes an internal usage-summary read endpoint for the web BFF, and calls the private search API through a generated internal client derived from the authoritative OpenAPI snapshot.
- **Update Rule:** Requirement-level public/private boundary constraints remain stable while MCP endpoint paths, token-exchange settings, quota policy, usage ledger shape, and MCP tool schema stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - MCP JSON-RPC requests over Streamable HTTP.
  - `Authorization: Bearer <logto-personal-access-token>` from MCP clients.
  - Logto token endpoint responses from PAT token exchange.
  - Logto OIDC discovery and JWKS documents for access-token validation.
  - Redis-backed quota counters and token-exchange cache.
  - MCP PostgreSQL database connection for MCP-owned usage records.
  - Private FastAPI search responses from `GET /api/v1/search`.
- **Outputs:**
  - MCP initialization, tool-listing, and tool-call responses.
  - `search` tool results containing `matched_cards` and `connected_titles`.
  - Public auth failures that do not disclose token contents.
  - Quota failures with retry guidance when available.
  - Usage records attributed to both user subject and PAT fingerprint.
  - Internal usage-summary responses keyed by PAT fingerprint for BFF Dashboard consumption.
- **Artifacts:**
  - `apps/mcp` Python workspace member.
  - MCP service tests.
  - Generated internal Python API client artifacts under `packages/contracts/generated/python/` derived from `packages/contracts/openapi/openapi.json`.
  - MCP-owned Alembic migration assets for durable MCP-owned usage records.
  - Dockerfile, role startup command, dedicated PostgreSQL service, compose service definitions, and nginx route for the MCP surface.

## Design Approach
- **Approach:** The repository exposes public model access through a dedicated MCP service rather than the browser BFF or private FastAPI app. The MCP service owns protocol handling, token exchange, quota enforcement, and usage attribution. Search execution is delegated to the private FastAPI search endpoint through generated internal contract artifacts, preserving the existing search module as the ranking and response-shape owner.
- **Key Elements:**
  - **MCP runtime:** `apps/mcp` runs a Python MCP server using the official MCP Python SDK with Streamable HTTP transport.
  - **Public endpoint:** Production routes `/mcp` on the public application host to the MCP service through the project-local nginx app gateway. The endpoint supports the MCP Streamable HTTP POST/GET contract.
  - **Tool contract:** The service exposes exactly one tool named `search`. The input schema requires non-empty `query`. The output mirrors the private search contract: `matched_cards[]` with `node_id`, `current_version`, `title`, and `content`, plus `connected_titles[]`.
  - **PAT-backed authentication:** MCP clients send a Logto personal access token in the bearer header. The MCP service does not persist raw PATs, does not log them, and does not treat them as repository-owned API keys.
  - **Token exchange:** The MCP service uses a configured first-party Logto application credential to exchange the PAT for an access token with the MCP API resource audience and search scope. This is one service-owned token-exchange client, not one Logto application per user, token, device, or external model client.
  - **Access-token validation:** After token exchange, the service validates the resulting access token against the configured issuer, audience/resource, required search scope, expiration, and JWKS signing key. The user account identity is the token `sub`.
  - **Token fingerprint:** For quota and audit, the service computes a server-secret HMAC fingerprint of the presented PAT. The canonical fingerprint format is `pat_` plus lowercase hexadecimal HMAC-SHA256 of the raw PAT bytes using `KNOWLEDGE_MCP_PAT_FINGERPRINT_SECRET` as UTF-8 bytes. The active secret must be at least 32 characters. Raw PATs never enter logs, database rows, Redis values, response payloads, or generated request IDs.
  - **Two-level accounting:** Durable usage records and quota decisions include both user-level identity (`sub`) and token-level identity (`pat_fingerprint`). Billing and plan entitlement are user-level. Token-level records support device audit, suspicious-token investigation, targeted limiting, and operational debugging.
  - **Quota state:** Redis stores short-window and longer-window quota counters using MCP-owned key prefixes. User-level counters enforce account quota. PAT-level counters enforce per-token guardrails.
  - **Usage ledger:** PostgreSQL stores durable usage events for successful tool calls and rejected quota outcomes. Each record includes timestamp, request ID, tool name, user subject, PAT fingerprint, unit cost, outcome, and safe error code when applicable.
  - **Internal usage summary:** The MCP service exposes `POST /internal/dashboard/usage-summary` as a service-authenticated internal HTTP endpoint for BFF Dashboard consumption. The endpoint accepts `{ patFingerprints: string[] }`, deduplicates valid fingerprints, rejects malformed fingerprints and oversized batches with `400`, and returns `{ summaries: [{ patFingerprint, successfulSearchCount, lastUsedAt }] }`. Each requested unique fingerprint has a response row; fingerprints without usage return `successfulSearchCount: 0` and `lastUsedAt: null`. The endpoint is not a public MCP endpoint, is not listed as an MCP tool, and never accepts or returns raw PAT values.
  - **Internal usage-summary auth:** BFF calls to the internal usage-summary endpoint use a Logto-issued service-to-service bearer access token with the configured MCP internal API resource/audience and `usage:read` scope. MCP validates issuer, audience, scope, expiry, and allowed service client identity before reading usage summaries.
  - **Database ownership boundary:** `apps/mcp` owns a dedicated PostgreSQL service for its durable usage ledger, plus its table metadata, Alembic environment, revisions, and Alembic version table. MCP usage tables use that database's default schema. It must not register MCP persistence models in `apps/api` Alembic or read/write graph, taxonomy, ingestion, source-pipeline, or job-queue linkage tables directly.
  - **Token-exchange cache:** Redis may cache exchanged access tokens by PAT fingerprint until access-token expiry with a safety margin. PAT revocation is enforced once cached access expires or immediately when exchange is retried and Logto rejects the PAT.
  - **Private search access:** The MCP service calls private `GET /api/v1/search` over the backend Docker network using a generated internal Python client derived from the OpenAPI artifact. It does not import FastAPI route internals or graph persistence internals.
  - **Error handling:** Authentication failure maps to MCP-compatible auth errors without exposing token text. Quota failure returns a tool error that includes safe retry metadata. Internal search dependency failures preserve correlation through logs and safe MCP error content.
  - **Origin and transport security:** Streamable HTTP requests without an `Origin` header are accepted for non-browser MCP clients. Requests with an `Origin` header are accepted only when the origin matches the configured MCP allowed-origin list. Production serves the public MCP endpoint only through HTTPS at the shared proxy boundary.
- **Interactions:**
  1. User creates a Logto personal access token while signed in to the knowledge system.
  2. User configures an MCP client with the public MCP endpoint and bearer PAT.
  3. MCP client initializes the MCP session and lists tools.
  4. For each MCP request, the service extracts the bearer PAT, computes its HMAC fingerprint, exchanges or cache-resolves the short-lived access token, and validates issuer, audience, scope, and subject.
  5. The service checks account-level and token-level quota before executing `search`.
  6. The `search` tool calls the private search API over Docker-network HTTP and returns the search response as MCP tool content.
  7. The service records usage with user subject, PAT fingerprint, tool name, unit cost, outcome, and request correlation metadata.
  8. The web BFF requests usage summaries for known PAT fingerprints through the internal usage-summary endpoint using service-to-service bearer authentication.

## Validation
- **Checks:**
  - MCP tool contract tests verify initialization, tool listing, `search` input validation, and successful search result shape, including `node_id` and `current_version` on each matched card.
  - Auth tests verify missing bearer rejection, malformed PAT rejection, token-exchange failure handling, issuer mismatch rejection, audience mismatch rejection, missing scope rejection, expired token rejection, and JWKS key rotation refresh.
  - Security tests verify raw PAT values are absent from logs, Redis values, database rows, and response payloads.
  - Architecture tests verify `apps/mcp` does not import `apps/api/src/**` and does not access non-MCP database tables directly.
  - Quota tests verify user-level accounting, PAT-level accounting, quota rejection, retry metadata, and usage-event persistence for accepted and quota-rejected calls.
  - Usage-summary tests verify service authentication, PAT-fingerprint filtering, lifetime successful search-call counts, latest usage timestamp calculation, and absence of raw PAT values in request and response payloads.
  - Migration ownership tests verify MCP usage persistence is registered only under `apps/mcp` Alembic and uses the dedicated MCP database default schema.
  - Internal API adapter tests verify generated client usage for `GET /api/v1/search`, matched-card `node_id/current_version/title/content` mapping, and safe mapping of private API failures.
  - Compose/config tests verify `mcp` receives MCP-specific Logto, Redis, internal API, quota, and logging settings; production nginx exposes `/mcp`; production `/api/v1/*` remains private.
  - Contract drift checks verify the generated internal client is current with `packages/contracts/openapi/openapi.json`.
- **Evidence:**
  - Active specs describe `apps/mcp` as the public programmatic search boundary without conflicting browser BFF or private API route exposure claims.
  - Targeted MCP service tests pass for protocol, auth, quota, usage attribution, and internal search adapter behavior.
  - Contract generation verification passes for internal API client artifacts.
  - Compose and nginx inspection confirms the MCP route is public while the private FastAPI service remains internal.

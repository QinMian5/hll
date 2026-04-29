---
abstract: MCP-only append-only agent search analytics design for successful search tool calls and future offline path analysis.
out_of_scope: Browser web analytics, failed-search observability, quota accounting, performance monitoring, and online ranking updates.
---

# Design: mcp-agent-search-analytics

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Preserve MCP agent search facts needed for future offline analysis of agent search sessions, query trajectories, result exposure, and search-driven graph or ranking iteration.
- **Scope/Boundaries:** Covers MCP-only successful `search` tool-call analytics, MCP session attribution, query text and hash capture, result exposure snapshots, PostgreSQL append-only storage, and ClickHouse-ready export markers. Excludes browser web searches, browser clicks, failed search diagnostics, latency analysis, quota/audit ledgers, and online ranking changes.
- **Related Requirements:** R-001, R-004, R-005, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Public programmatic access must remain owned by the MCP service; module boundaries must prevent MCP analytics state from coupling to browser web surfaces or private API persistence; runtime behavior must remain reproducible through repository-owned PostgreSQL and Alembic assets; active specs must stay synchronized with behavior-changing MCP analytics decisions.
- **Detail Commitments:** `apps/mcp` owns an append-only `agent_search_events` table in the MCP PostgreSQL database. The table stores only successful MCP `search` tool-call analytics facts. It stores raw query text, a normalized query hash, the MCP session identifier, user/token attribution, result exposure snapshots, and export state for a future ClickHouse pipeline. It does not store error rows, latency fields, client implementation metadata, browser session identifiers, parent search identifiers, or previous event identifiers.
- **Update Rule:** Requirement-level public/private and module-boundary constraints remain stable while MCP analytics table shape, event capture semantics, session attribution, and export details stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Successful MCP `search` tool calls.
  - MCP session identifiers from Streamable HTTP session handling.
  - Authenticated MCP caller identity after PAT exchange and access-token validation.
  - PAT fingerprints computed by the MCP service.
  - Raw `query` values submitted to the MCP `search` tool.
  - Private search API responses returned from `GET /api/v1/search`.
- **Outputs:**
  - One durable append-only analytics row per successful MCP `search` tool call.
  - Query text and hash records for future query reformulation and aggregation analysis.
  - Session-scoped, timestamp-ordered search event streams for offline path analysis.
  - Result exposure snapshots containing matched node ids and ranks.
  - Nullable export markers for future ClickHouse transfer jobs.
- **Artifacts:**
  - `apps/mcp` SQLAlchemy metadata for `agent_search_events`.
  - `apps/mcp` Alembic revision for the analytics table and indexes.
  - MCP service capture logic around successful `search` tool calls.
  - Unit and integration tests under `apps/mcp/tests`.

## Design Approach
- **Approach:** Store MCP agent search analytics as first-party append-only facts inside the MCP-owned PostgreSQL database. The capture path records only successful `search` tool calls after the private search response is available, so the table represents analyzable search exposures rather than general runtime behavior. Offline analysis later reconstructs paths by ordering rows by `mcp_session_id` and `occurred_at`.
- **Key Elements:**
  - **MCP-only scope:** The analytics table records MCP agent searches only. Browser web searches, browser result clicks, anonymous web principals, and web session cookies are outside the table's scope.
  - **Successful-search-only semantics:** Rows are created only for successful MCP `search` tool calls that receive a valid private search response. Authentication failures, quota failures, validation failures, dependency failures, and private search failures are represented by existing logs and usage/audit paths, not by `agent_search_events`.
  - **Session attribution:** Each row stores `mcp_session_id`. The MCP service uses the Streamable HTTP session identifier when available and a server-generated MCP session identifier when the runtime needs one. The table does not store parent search ids or previous event ids.
  - **Time ordering:** Each row stores database-generated `occurred_at` using PostgreSQL `now()`. Path segmentation rules, inactivity timeouts, and cross-session analysis are offline analysis concerns and are not applied during capture.
  - **Query facts:** Each row stores `raw_query` and `query_hash`. The hash is derived from a deterministic normalization rule owned by the MCP analytics module so repeated equivalent queries can be grouped without losing raw text for future analysis.
  - **Result exposure snapshot:** Each row stores `matched_count`, `connected_count`, and `matched_results`. `matched_results` is a JSONB array ordered by rank, with each item shaped as `{ "node_id": <integer>, "rank": <integer> }`. The MVP snapshot does not invent score or ranking-feature fields when the private search response does not provide them.
  - **Algorithm version:** Each row stores integer `search_algorithm_version` so future offline analysis can separate events produced by different ranking implementations. Version values start at `1` and increment when the search ranking implementation changes.
  - **ClickHouse outlet:** Each row stores nullable `exported_at`, defaulting to `NULL` in PostgreSQL. Future export jobs can mark rows after transfer to ClickHouse without changing the successful-search capture contract.
  - **Append-only rule:** The capture path inserts rows only and lets PostgreSQL generate `id`, `occurred_at`, and default `exported_at`. It does not update or delete analytics facts except for setting `exported_at` in a future export workflow.
  - **Table shape:** `agent_search_events` has integer primary key `id`, `occurred_at`, `user_sub`, `pat_fingerprint`, `mcp_session_id`, `raw_query`, `query_hash`, `matched_count`, `connected_count`, `matched_results`, integer `search_algorithm_version`, and nullable `exported_at`. The table does not store request correlation ids because offline path analysis uses session and time ordering.
  - **Indexes:** The table supports session path reads by `(mcp_session_id, occurred_at)`, user-level analysis by `(user_sub, occurred_at)`, token-level analysis by `(pat_fingerprint, occurred_at)`, query aggregation by `(query_hash, occurred_at)`, and future export scans by rows where `exported_at IS NULL`.
- **Interactions:**
  1. MCP client establishes or reuses an MCP session.
  2. MCP client calls the `search` tool with a non-empty query.
  3. MCP auth and quota flows resolve `user_sub` and `pat_fingerprint`.
  4. MCP service calls the private FastAPI search API through the generated internal client.
  5. MCP service receives a successful search response.
  6. MCP service inserts one `agent_search_events` row with query, identity, session, result exposure, and algorithm-version facts.
  7. MCP service returns the search tool result to the MCP client.
  8. Future offline jobs query PostgreSQL or export unmarked rows to ClickHouse for path and ranking analysis.

## Validation
- **Checks:**
  - Migration ownership tests verify `agent_search_events` is registered only under `apps/mcp` Alembic and the MCP database.
  - Model projection tests verify table columns, JSONB result snapshot storage, and required indexes.
  - Capture tests verify one successful MCP `search` tool call creates one analytics row with `raw_query`, `query_hash`, `mcp_session_id`, attribution fields, matched counts, matched result ranks, and algorithm version.
  - Capture tests verify failed authentication, quota rejection, input validation failure, private search failure, and analytics-excluded failure paths do not create `agent_search_events` rows.
  - Session tests verify the capture path records the active MCP session identifier.
  - Security tests verify raw PAT values are absent from analytics rows and only PAT fingerprints are stored.
  - Architecture tests verify browser web code, private FastAPI modules, and source-pipeline modules do not import or write MCP analytics persistence.
- **Evidence:**
  - Active specs define MCP agent-search analytics as a dedicated MCP-owned append-only fact table.
  - Targeted MCP migration, model, capture, session, security, and architecture tests pass.
  - Database inspection shows `agent_search_events` exists only in the MCP PostgreSQL database.

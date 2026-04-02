---
abstract: Global API error governance for unified client contract, layered semantics, and fail-fast observability across runtime and startup paths.
out_of_scope: Endpoint-level business error catalogs, frontend copy customization workflows, and external incident platform integrations.
---

# Design: 13-global-error-governance

## Active Truth Policy
- This document defines only currently accepted global error-governance decisions.
- Superseded error-governance decisions are removed from active text.

## Context
- **Purpose:** Establish a stable, extensible global error contract for MVP that can evolve into a public-facing service without contract rewrites.
- **Scope/Boundaries:** Covers error semantics, HTTP mapping, startup/runtime behavior, logging obligations, and extension governance.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.
- **Related Designs:** `03-architecture-constraints`, `04-repository-structure`, `07-quality-engineering`, `09-database-runtime-access`.
- **Precedence Rule:** For error-path response/logging/request-correlation behavior, this document is authoritative if any other document defines a conflicting default.

## Design Goals
- Keep MVP implementation lightweight while freezing long-lived public error contracts.
- Enforce fail-fast behavior for known invalid states and startup-critical failures.
- Ensure every error is traceable for debugging and production incident response.
- Prevent transport semantics from leaking into domain/application internals.

## Global Error Contract

### Unified Error Envelope
All API-visible errors must use one response structure:

```json
{
  "error": {
    "code": "INFRA_DB_CONNECTION_UNAVAILABLE",
    "message": "Database is temporarily unavailable.",
    "details": {},
    "hint": "Retry later or contact support if the issue persists.",
    "request_id": "req_01JABCDEFG123456789"
  }
}
```

### Field Contract
- `error.code`: required non-empty string from `ErrorCode(StrEnum)` value; machine-consumable primary contract key.
- `error.message`: required non-empty string; human-readable summary.
- `error.details`: required object; defaults to `{}` when no safe structured details exist.
- `error.hint`: required non-empty string; actionable and safe guidance for callers.
- `error.request_id`: required non-empty string; correlates response with logs.
- Every exposed `error.code` must use an explicit non-empty `hint`; implicit fallback hints are forbidden.

### Non-Disclosure Rule
- Stack traces, raw exception text, SQL text/parameters, credentials, tokens, full DSNs, and unfiltered request bodies must not appear in API responses.

## Error Code Governance

### Naming Contract
- Error code value format is `<DOMAIN>_<CATEGORY>_<DETAIL>`.
- Error codes are defined centrally through `ErrorCode(StrEnum)`.
- Runtime/business code must not perform string-format validation for error codes.
- Error code format correctness is enforced by unit-test gates.
- `error.code` is stable after exposure; message/hint text may evolve.
- HTTP status must not be encoded into `error.code`.

### Allowed Domain Segment Values
- `DOMAIN`: domain truth and business-rule errors.
- `APPLICATION`: orchestration/use-case flow errors, including API request-shape/input-invalid failures.
- `INFRA`: infrastructure/dependency/configuration/runtime platform failures.
- `INTERNAL`: unknown/unexpected internal failures.

### Category Segment Rule
- `CATEGORY` must map to stable repository capability boundaries such as `API`, `KNOWLEDGE`, `SEARCH`, `DB`, `CONFIG`.
- Temporary implementation names are forbidden in `CATEGORY`.

## Error Semantics and Layer Boundaries

### Minimal Error Class Tree
```text
AppError
├── DomainError
├── ApplicationError
├── InfrastructureError
└── InternalError
```

### Layer Ownership
- `api` layer:
  - owns request/transport parsing and response adaptation.
  - must not be the long-term owner of domain or infrastructure semantics.
- `service` layer:
  - raises `DomainError` and `ApplicationError`.
  - must not depend on `HTTPException` or other transport-specific exceptions.
- `repo/shared` layers:
  - translate database/dependency failures into `InfrastructureError`.
  - must not leak raw driver/ORM exceptions to upper layers.

## HTTP Mapping Baseline
- Request structure validation errors map to `422` and use `APPLICATION_API_INPUT_INVALID`.
- Domain/application errors map by semantic subtype:
  - not found: `404`
  - conflict/invalid state: `409`
  - semantic rule violation: `422`
  - request-side use-case input issue: `400`
- Infrastructure errors map by operational semantics:
  - temporary dependency unavailable: `503`
  - non-classified infrastructure/internal platform failure: `500`
- Unknown uncaught exceptions map to `500` with `INTERNAL_API_UNEXPECTED_ERROR`.
- Ingestion acceptance endpoint keeps asynchronous acceptance semantics:
  - valid payloads return `202` after request acceptance.
  - downstream enqueue/worker failures are internal-only and do not alter the accepted response.

## Deterministic Mapping Contract
- `DOMAIN_*` uses a minimum frozen subtype set:
  - `DOMAIN_<CATEGORY>_RESOURCE_NOT_FOUND` -> `404`
  - `DOMAIN_<CATEGORY>_STATE_CONFLICT` -> `409`
  - `DOMAIN_<CATEGORY>_RULE_VIOLATION` -> `422`
  - other `DOMAIN_*` fallback -> `422`
- `APPLICATION_*` uses a minimum frozen subtype set:
  - `APPLICATION_<CATEGORY>_INPUT_INVALID` -> `400`
  - `APPLICATION_<CATEGORY>_STATE_CONFLICT` -> `409`
  - `APPLICATION_<CATEGORY>_RULE_VIOLATION` -> `422`
  - other `APPLICATION_*` fallback -> `422`
- Special-case override:
  - `APPLICATION_API_INPUT_INVALID` -> `422` (request-shape validation contract).
  - ingestion accepted request -> `202` (asynchronous acceptance contract).
- A request returns exactly one error (fail-fast). Aggregated multi-error payloads are out of MVP scope.
- If multiple application subtypes are detected in one validation path, priority is fixed:
  1. `input_invalid`
  2. `state_conflict`
  3. `rule_violation`
- If multiple domain subtypes are detected in one validation path, priority is fixed:
  1. `resource_not_found`
  2. `state_conflict`
  3. `rule_violation`

## 422 Boundary Rule
- `APPLICATION_API_INPUT_INVALID` under `422` means transport/schema-level request-shape invalidity.
- Business semantic failures must use `DOMAIN_*` or `APPLICATION_*` even if status also maps to `422`.
- Clients must branch by `error.code`, not by status/message text.

## Runtime Error Handling Flow
1. Middleware extracts or generates `request_id`.
2. Request processing executes API -> service -> repo flow.
3. Known framework validation errors are normalized to unified envelope.
4. Known `AppError` subclasses are mapped to status + envelope.
5. Unknown exceptions are wrapped as internal errors.
6. All errors are logged with required context.
7. Client receives unified envelope with same `request_id` used in logs.

## Startup Fail-Fast Flow
- Startup bootstrap logger must initialize before startup-critical checks.
- Bootstrap logger exists only to surface startup failures before runtime logging is fully configured.
- Settings load errors and DB-initialization errors must fail startup immediately.
- Startup failures do not produce HTTP responses, but must use the same error-code governance and logging field policy.
- Development-only relaxed startup behavior may be enabled explicitly; production baseline remains strict fail-fast.

### Startup Sequence Matrix
| Stage | Action | Failure Outcome | Required Log Channel |
|---|---|---|---|
| S1 | Initialize bootstrap stderr logger | fail process if logger cannot initialize | process stderr |
| S2 | Generate startup `request_id` | regenerate until valid | bootstrap stderr logger |
| S3 | Load settings | fail-fast | bootstrap stderr logger |
| S4 | Initialize runtime logger (console + file) | fail-fast | bootstrap stderr logger for failure record |
| S5 | Run DB startup readiness checks | fail-fast | runtime logger when available; otherwise bootstrap stderr logger |

## Startup Error Correlation Contract
- Startup failures must still emit a non-empty correlation identifier.
- When request context is unavailable, startup error logs must generate a correlation ID compatible with request-ID format policy.
- Startup log field name for this identifier is `request_id` (same key as runtime error logs).
- Startup error logs must include:
  - generated `request_id`
  - `error.code`
  - `startup_phase`
  - `exception_class`
  - cause-chain/stack-trace metadata
- Startup error paths do not emit API response envelopes; correlation and semantic identity are guaranteed through logs.

## Request ID Governance
- API accepts inbound `X-Request-ID` only when it passes format validation.
- Missing or invalid inbound value triggers server-side generation of a new request ID.
- Response includes the final request ID in both:
  - response payload field: `error.request_id`
  - response header: `X-Request-ID`
- Minimum inbound validation contract:
  - length: `8..128`
  - charset: `[A-Za-z0-9._:-]`
  - regex baseline: `^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$`
- Invalid inbound IDs are discarded and regenerated; original invalid value must not be echoed to clients.

## Logging and Debuggability Governance

### Mandatory Logging Rule
- Every handled and unhandled error must be logged.
- 5xx and unknown errors must preserve full exception stack trace and cause chain.

### Required Runtime Error Log Context (request path)
- `request_id`
- `error.code`
- `http_status`
- `path`
- `method`
- `exception_class`
- cause-chain/stack-trace metadata

### Required Startup Error Log Context (no request path)
- `request_id` (generated startup correlation identifier)
- `error.code`
- `startup_phase`
- `exception_class`
- cause-chain/stack-trace metadata

### Safe vs Internal Details
- Error data is split into:
  - `safe_details`: allowed in response `error.details`
  - `log_details`: internal debug context for logs only
- Unknown/unapproved fields must not enter response payloads.

## Security and Redaction Policy
- Never log or return secrets/tokens/passwords/session identifiers.
- Never return raw DB exceptions/queries/DSNs to clients.
- Redaction is mandatory before logging high-risk input-originated values.

## Extensibility Governance
- New capabilities must use a stable `CATEGORY` segment before exposing new error codes.
- New error codes must satisfy naming contract and non-duplication checks.
- Existing exposed `error.code` values are contract-stable and cannot be silently renamed.
- Error catalog expansion is incremental and capability-driven; no speculative global mega-catalog is introduced in MVP.

## Validation
- All API-visible errors conform to unified envelope and non-null `hint`.
- Validation errors are normalized to status `422` with stable `APPLICATION_API_INPUT_INVALID` code.
- Unknown internal errors still require explicit non-empty `hint`.
- `DOMAIN_*` and `APPLICATION_*` mappings follow frozen subtype sets and deterministic priorities.
- Infrastructure temporary-unavailability cases return `503` except accepted-ingestion asynchronous downstream failures; unknown internals return `500`.
- Ingestion endpoint returns `202` on valid accepted payloads while preserving internal log observability for downstream asynchronous failures.
- Startup-critical config/DB failures are fail-fast and log-observable.
- Logs for every error path carry `request_id` and semantic error identity.

### Compliance Matrix
| Rule | Verification Method | Owner Layer | Gate |
|---|---|---|---|
| Envelope fields exist and `hint` is non-null/non-empty | unit tests for payload builders | `core/errors.py` | `test` |
| `ErrorCode` values follow `<DOMAIN>_<CATEGORY>_<DETAIL>` | unit tests over enum values | `core/errors.py` | `test` |
| Validation errors map to `422` + `APPLICATION_API_INPUT_INVALID` | unit/integration handler tests | `core/error_handlers.py` + `api` | `test` |
| `DOMAIN_*`/`APPLICATION_*` deterministic subtype mapping and priority | unit handler mapping tests | `core/error_handlers.py` | `test` |
| `503` vs `500` split for infrastructure/unknown errors | integration runtime-path tests | `shared/db` + `core/error_handlers.py` | `test` |
| Accepted-ingestion contract keeps `202` for valid payloads with downstream failures handled internally | integration tests for ingestion endpoint plus worker failure scenarios | `modules/ingestion` + `core/error_handlers.py` | `test` |
| Runtime request-id propagation to payload/header/logs | middleware + handler integration tests | `core/request_id.py` + `api` | `test` |
| Startup fail-fast with startup `request_id` logging | startup integration tests | `core/config.py` + `shared/db/session.py` + `main.py` | `test` |
| Startup sequence S1..S5 behavior and logger-channel guarantees | startup integration tests with controlled failure injection | `main.py` + `core/logging.py` + `core/config.py` | `test` |
| Error envelope exposure in OpenAPI contract | contract tests against OpenAPI schema | `api` + `packages/contracts` | `contract drift` |

## Deferred to Later Phases
- Full module-by-module exhaustive error code catalogs.
- Internationalization strategy for message/hint text.
- External alert routing and SLO-linked incident automation.

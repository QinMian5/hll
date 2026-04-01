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
    "code": "infra.db.connection_unavailable",
    "message": "Database is temporarily unavailable.",
    "details": {},
    "hint": "Retry later or contact support if the issue persists.",
    "request_id": "req_01JABCDEFG123456789"
  }
}
```

### Field Contract
- `error.code`: required non-empty string; machine-consumable primary contract key.
- `error.message`: required non-empty string; human-readable summary.
- `error.details`: required object; defaults to `{}` when no safe structured details exist.
- `error.hint`: required non-empty string; actionable and safe guidance for callers.
- `error.request_id`: required non-empty string; correlates response with logs.
- Every exposed `error.code` must define a default non-empty `hint`.
- Unknown internal exceptions must use a fixed fallback hint:
  - `"Retry later or contact support with the provided request_id."`

### Non-Disclosure Rule
- Stack traces, raw exception text, SQL text/parameters, credentials, tokens, full DSNs, and unfiltered request bodies must not appear in API responses.

## Error Code Governance

### Naming Contract
- Error codes are formatted as `<category>.<module>.<name>`.
- `error.code` is stable after exposure; message/hint text may evolve.
- HTTP status must not be encoded into `error.code`.

### Allowed Categories
- `presentation`: transport/parsing/shape-level request errors.
- `domain`: domain truth and business-rule errors within a module.
- `application`: orchestration/use-case flow errors across module operations.
- `infra`: infrastructure/dependency/configuration/runtime platform failures.
- `internal`: unknown/unexpected internal failures.

### Module Segment Rule
- `module` must map to stable repository capability boundaries such as `api`, `knowledge`, `search`, `db`, `config`.
- Temporary implementation names are forbidden in `module`.

## Error Semantics and Layer Boundaries

### Minimal Error Class Tree
```text
AppError
├── PresentationError
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
- Request structure validation errors map to `422` and use `presentation.api.request_validation_failed`.
- Domain/application errors map by semantic subtype:
  - not found: `404`
  - conflict/invalid state: `409`
  - semantic rule violation: `422`
  - request-side use-case input issue: `400`
- Infrastructure errors map by operational semantics:
  - temporary dependency unavailable: `503`
  - non-classified infrastructure/internal platform failure: `500`
- Unknown uncaught exceptions map to `500` with `internal.api.unexpected_error`.

## Deterministic Mapping Contract
- `application.*` uses a minimum frozen subtype set:
  - `application.<module>.input_invalid` -> `400`
  - `application.<module>.state_conflict` -> `409`
  - `application.<module>.rule_violation` -> `422`
  - other `application.*` fallback -> `422`
- A request returns exactly one error (fail-fast). Aggregated multi-error payloads are out of MVP scope.
- If multiple application subtypes are detected in one validation path, priority is fixed:
  1. `input_invalid`
  2. `state_conflict`
  3. `rule_violation`

## 422 Boundary Rule
- `presentation.*` under `422` means transport/schema-level request-shape invalidity.
- Business semantic failures must use `domain.*` or `application.*` even if status also maps to `422`.
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
- Logging must initialize before startup-critical checks.
- Settings load errors and DB-initialization errors must fail startup immediately.
- Startup failures do not produce HTTP responses, but must use the same error-code governance and logging field policy.
- Development-only relaxed startup behavior may be enabled explicitly; production baseline remains strict fail-fast.

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

### Required Error Log Context
- `request_id`
- `error.code`
- `http_status` when applicable
- `path`
- `method`
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
- New modules must register and use a stable `module` segment before exposing new error codes.
- New error codes must satisfy naming contract and non-duplication checks.
- Existing exposed `error.code` values are contract-stable and cannot be silently renamed.
- Error catalog expansion is incremental and module-driven; no speculative global mega-catalog is introduced in MVP.

## Validation
- All API-visible errors conform to unified envelope and non-null `hint`.
- Validation errors are normalized to status `422` with stable presentation error code.
- Unknown internal errors always use fixed fallback `hint` text.
- `application.*` mapping follows frozen subtype set and deterministic priority.
- Infrastructure temporary-unavailability cases return `503`; unknown internals return `500`.
- Startup-critical config/DB failures are fail-fast and log-observable.
- Logs for every error path carry request correlation and semantic error identity.

## Deferred to Later Phases
- Full module-by-module exhaustive error code catalogs.
- Internationalization strategy for message/hint text.
- External alert routing and SLO-linked incident automation.

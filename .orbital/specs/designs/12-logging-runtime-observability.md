---
abstract: Minimal MVP logging design for unified process initialization and console plus rotating-file output.
out_of_scope: Request correlation identifiers, global error-governance refactor, external log shipping, and tracing or metrics rollout.
---

# Design: 12-logging-runtime-observability

## Active Truth Policy
- This document describes only the currently accepted MVP logging behavior.
- Superseded logging decisions are removed from active text.
- Scope is limited to runtime logging initialization and consumption patterns.

## Context
- Purpose: deliver a minimal logging baseline that is immediately useful for debugging and extensible for later production hardening.
- Scope/Boundaries: startup initialization contract, handler topology, rotation policy, logger usage pattern, and entrypoint ownership.
- Related Requirements: R-001, R-004, R-005, R-006.
- Related Designs: `04-repository-structure`, `13-global-error-governance`.

## MVP Logging Goals
- Runtime logs must appear in console output.
- Runtime logs must persist to one rotating file.
- Logging initialization must be centralized and deterministic per process.
- Non-entrypoint modules must consume logger instances without performing logging setup.
- The design must keep extension points open without introducing additional logging frameworks in this round.

## Logging Module Contract
- `apps/api/src/core/logging.py` is the single logging-infrastructure module.
- The module exposes only:
  - `configure_logging(...)`: process-level logging initialization.
  - `get_logger(name)`: module-level logger retrieval.
- Logging setup is idempotent: repeated calls in the same process must not duplicate handlers.

## Handler Topology
- Python process root logger (`logging.getLogger()`) owns exactly two handlers after initialization:
  1. `StreamHandler` for console output.
  2. `RotatingFileHandler` for file persistence.
- Application loggers are descendants and do not own handlers.
- Both handlers use one shared text formatter that includes:
  - timestamp
  - level
  - logger name
  - log message
- JSON formatting is deferred.

## Rotation Policy
- Rotation strategy is size-based.
- MVP baseline values:
  - `LOG_FILE_MAX_BYTES=10485760` (10MB)
  - `LOG_FILE_BACKUP_COUNT=5`
- Rotation stays in the same directory as the main log file.

## Configuration Policy
- Logging values are configured at process startup through the existing settings entrypoint.
- MVP supports explicit configuration for:
  - `LOG_LEVEL`
  - `LOG_FILE_PATH`
  - `LOG_FILE_MAX_BYTES`
  - `LOG_FILE_BACKUP_COUNT`
- Required key:
  - `LOG_FILE_PATH`
- Defaulted keys:
  - `LOG_LEVEL=INFO`
  - `LOG_FILE_MAX_BYTES=10485760` (10MB)
  - `LOG_FILE_BACKUP_COUNT=5`
- `LOG_NAMESPACE_ROOT` is not required in this round.
- This round does not add request-correlation-specific configuration.

## Entrypoint Ownership
- Logging initialization is performed only in process entrypoints.
- API process bootstrap initializes logging once in `apps/api/src/entrypoints/api/bootstrap.py` before serving requests.
- Worker process bootstrap initializes logging once in `apps/api/src/entrypoints/worker/bootstrap.py` before actor registration and execution.
- Business modules import `get_logger(__name__)` (or `logging.getLogger(__name__)` where unchanged) and must not configure handlers.

## Failure Behavior
- Known logging setup errors must fail explicitly during entrypoint startup.
- `LOG_FILE_PATH` parent-directory policy:
  - if parent directory is missing, runtime may create it.
  - if parent path exists but is not a directory, startup must fail.
  - if directory creation fails, startup must fail.
  - if target directory is not writable, startup must fail.
- Silent fallback behavior for failed handler setup is forbidden.
- Runtime continues only after successful logging initialization.

## Error and Request-ID Boundary for This Round
- This round does not introduce a new request-ID module.
- This round does not expand global error-governance contracts.
- Existing error contracts may continue to emit current fields, but logging work in this round must not depend on new request-correlation mechanisms.
- Error logs must remain debug-usable through semantic fields such as `event`, `error_code` (when present), and `exception_class`.

## Deferred to Later Phases
- Dedicated per-namespace files.
- Remote log shipping backends.
- JSON structured logging.
- Request-correlation governance redesign.

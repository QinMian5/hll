---
abstract: Runtime logging design for API console/file output, namespace layering, and fail-fast initialization.
out_of_scope: External log aggregation platforms, tracing/metrics systems, and business-domain event taxonomy.
---

# Design: 12-logging-runtime-observability

## Active Truth Policy
- This document records only the currently accepted runtime logging decisions.
- Superseded logging choices are removed instead of kept as transition notes.
- Scope is limited to API runtime logging behavior and deployment-facing log persistence wiring.

## Context
- Purpose: define a production-usable and troubleshooting-oriented logging baseline for API runtime.
- Scope/Boundaries: logger namespace strategy, handler topology, rotation policy, configuration contract, startup failure policy, and Docker bind-mount policy.
- Related Requirements: R-001, R-004, R-005, R-006.
- Related Designs: `03-architecture-constraints`, `04-repository-structure`, `06-deployment-docker`, `13-global-error-governance`.

## Runtime Logging Objectives
- Logging serves local/server troubleshooting and deployment diagnostics.
- Runtime output must be visible in container console logs.
- Runtime output must also persist to one rotating file for local inspection.
- Logging behavior must fail explicitly on known invalid initialization states.

## Namespace Layering Model
- Logger hierarchy uses a single configurable namespace root.
- Module loggers are created as descendants under the root namespace.
- Descendant loggers propagate to process-root handlers.
- Single-file persistence is retained while preserving namespace segmentation in log records.

## Handler Topology
- Python process root logger (`logging.getLogger()`) owns exactly two handlers:
  1. text console handler (`StreamHandler`)
  2. text file handler (`RotatingFileHandler`)
- Application namespace loggers do not own handlers and rely on propagation.
- Both handlers use a unified text format including timestamp, level, logger name, and message.
- Structured JSON logging is explicitly deferred.

## File Rotation Policy
- Rotation strategy is size-based.
- Baseline limits:
  - `LOG_FILE_MAX_BYTES=10485760` (10MB)
  - `LOG_FILE_BACKUP_COUNT=5`
- Rotation is local file rollover within the same directory.

## Configuration Contract
- Logging configuration is loaded through the same single `pydantic-settings` entrypoint.
- Runtime sources follow the project precedence contract: `YAML < .env`.
- Active runtime logging keys are required (no implicit defaults):
  - `LOG_LEVEL`
  - `LOG_NAMESPACE_ROOT`
  - `LOG_FILE_PATH`
  - `LOG_FILE_MAX_BYTES`
  - `LOG_FILE_BACKUP_COUNT`
- Logging keys follow the same source policy as other runtime settings: YAML provides optional non-secret defaults and `.env` may override.
- Current deployment baseline path is:
  - `LOG_FILE_PATH=/var/log/knowledge/api/app.log`

## Startup and Failure Policy
- Startup uses two stages:
  1. Bootstrap startup logger on stderr only (no file handler), for pre-settings failure visibility.
  2. Runtime logging initialization from validated settings using configured console + rotating-file handlers.
- Logging is initialized during API startup before business request handling.
- Initialization validates that the parent directory already exists, is a directory, and is writable.
- Automatic creation of the parent directory is forbidden.
- If target path is invalid, parent directory is missing, or path is not writable, startup must fail-fast and surface the original exception context.
- Silent runtime fallback to console-only mode is forbidden for known file-path setup failures.
- Bootstrap stderr logging is emergency startup instrumentation only and must not be treated as runtime fallback mode.
- Error-path request correlation semantics (`request_id` propagation and startup correlation behavior) are governed by `13-global-error-governance`.

## Docker Bind-Mount Policy
- Log file persistence uses host bind mount, not Docker named volume.
- Required mapping:
  - host: `<repo-root>/logs/api/`
  - container: `/var/log/knowledge/api`
- Host directory is a deployment prerequisite and must be provisioned with writable permissions for the API runtime user before container startup.
- The mapped host directory is the operational log inspection location for local/server troubleshooting.

## Deferred to Later Phases
- Per-namespace dedicated files and multi-sink routing policies.
- Remote shipping sinks (for example ELK/Loki/Cloud logging backends).
- JSON structured logging schema.

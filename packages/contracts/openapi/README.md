---
abstract: Canonical OpenAPI export artifacts generated from the FastAPI app.
out_of_scope: Hand-edited schema changes and generated TypeScript clients.
---

# OpenAPI Artifacts

- `openapi.json` is generated from the FastAPI app in `apps/api`.
- Update it only through `pnpm export` in `packages/contracts`.
- `pnpm verify` fails if the checked-in OpenAPI artifact drifts from the backend route/schema contract.

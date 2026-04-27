---
abstract: Generated contract artifacts derived from backend OpenAPI.
out_of_scope: Hand-authored application adapters and render-layer view models.
---

# Generated Contract Artifacts

- `types.ts` is generated from `openapi/openapi.json` through `openapi-typescript`.
- `client.ts` is generated as the minimal `openapi-fetch` wrapper over the generated `paths` types.
- `python/` is generated as the focused Python internal client for repository-owned private API calls.
- Do not hand-edit generated files. Regenerate them through `pnpm generate:types`, `pnpm generate:client`, and `pnpm generate:python`.

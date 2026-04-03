---
abstract: Generated TypeScript contract artifacts derived from backend OpenAPI.
out_of_scope: Hand-authored frontend data adapters and render-layer view models.
---

# Generated Contract Artifacts

- `types.ts` is generated from `openapi/openapi.json` through `openapi-typescript`.
- `client.ts` is generated as the minimal `openapi-fetch` wrapper over the generated `paths` types.
- Do not hand-edit generated files. Regenerate them through `pnpm generate:types` and `pnpm generate:client`.

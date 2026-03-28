# Repository Structure Governance Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan ID:** `2026-03-28-repository-structure-plan`

**Goal:** Implement a strong-governance monorepo structure with contract-driven integration and enforceable repository boundaries.

**Architecture:** This plan migrates the current repository into `apps/api`, `apps/web`, and `packages/contracts` with a single top-level governance surface (`Makefile` + `scripts`). Backend remains domain-oriented (`knowledge`, `search`), frontend remains feature-first, and frontend API access is restricted to generated contract clients from backend-exported OpenAPI.

**Input Specs:**
- Requirements: `/Users/mianqin/Code/knowledge/.orbital/specs/requirements.md`
- Designs: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/repository-structure.md`

**Assumptions and Constraints:**
- Existing code starts from `backend/` and `frontend/` directories.
- Backend OpenAPI export remains the authoritative contract source.
- Generated contract artifacts are committed to version control.
- The project uses containerized standard deployment assets (`infra/compose`, `infra/env`).
- No hidden fallback behavior is introduced; failures are explicit and actionable.

**Decision Gates:** None pending.

**Tech Stack:** Python + FastAPI + Uvicorn, React + TypeScript + Vite, pnpm, uv, Docker Compose, GitHub Actions.

---

## File Structure Lock (Target State)

- Create/maintain:
  - `/Users/mianqin/Code/knowledge/apps/api/**`
  - `/Users/mianqin/Code/knowledge/apps/web/**`
  - `/Users/mianqin/Code/knowledge/packages/contracts/**`
  - `/Users/mianqin/Code/knowledge/infra/compose/**`
  - `/Users/mianqin/Code/knowledge/infra/env/**`
  - `/Users/mianqin/Code/knowledge/scripts/**`
  - `/Users/mianqin/Code/knowledge/Makefile`
  - `/Users/mianqin/Code/knowledge/.github/workflows/ci.yml`
- Remove or migrate:
  - `/Users/mianqin/Code/knowledge/backend/**` -> `/Users/mianqin/Code/knowledge/apps/api/**`
  - `/Users/mianqin/Code/knowledge/frontend/**` -> `/Users/mianqin/Code/knowledge/apps/web/**`

## Chunk 1: Governance Scaffold and Monorepo Moves

### Task T01: Establish Root Governance Surface

**Task ID:** `T01`  
**Commit Ownership:** Controller at task end (single commit)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/Makefile`
- Create: `/Users/mianqin/Code/knowledge/scripts/bootstrap.sh`
- Create: `/Users/mianqin/Code/knowledge/scripts/dev-up.sh`
- Create: `/Users/mianqin/Code/knowledge/scripts/dev-down.sh`
- Create: `/Users/mianqin/Code/knowledge/scripts/check-all.sh`
- Create: `/Users/mianqin/Code/knowledge/scripts/contracts.sh`
- Create: `/Users/mianqin/Code/knowledge/scripts/contracts-check.sh`
- Modify: `/Users/mianqin/Code/knowledge/README.md` (or create if missing)
- Test: `/Users/mianqin/Code/knowledge/scripts/test-smoke.sh`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/repository-structure.md` (only if command names change)

- [ ] **Step 1: Write the failing governance smoke test**

```bash
#!/usr/bin/env bash
set -euo pipefail
make -n bootstrap >/dev/null
make -n check >/dev/null
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/test-smoke.sh`  
Expected: FAIL because `Makefile` targets are missing.

- [ ] **Step 3: Implement minimal root governance artifacts**

- Add `Makefile` targets: `bootstrap`, `dev`, `down`, `contracts`, `contracts-check`, `test`, `check`.
- Implement scripts with explicit exit-on-error and no silent fallback.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/test-smoke.sh`  
Expected: PASS with all required targets resolvable.

- [ ] **Step 5: Controller commits task**

```bash
git add Makefile scripts/ README.md
git commit -m "chore(repo): [plan:2026-03-28-repository-structure-plan][task:T01] add root governance commands"
```

**Anti-pattern avoidance notes:**
- No workaround scripts that ignore errors.
- No silent fallback when required tools are missing.
- Keep scripts DRY by delegating repeated logic to shared helpers if repetition appears.

### Task T02: Move Applications to Strong-Governance Paths

**Task ID:** `T02`  
**Commit Ownership:** Controller at task end (single commit)

**Files:**
- Move: `/Users/mianqin/Code/knowledge/backend` -> `/Users/mianqin/Code/knowledge/apps/api`
- Move: `/Users/mianqin/Code/knowledge/frontend` -> `/Users/mianqin/Code/knowledge/apps/web`
- Modify: `/Users/mianqin/Code/knowledge/Makefile`
- Modify: `/Users/mianqin/Code/knowledge/scripts/bootstrap.sh`
- Test: `/Users/mianqin/Code/knowledge/scripts/test-paths.sh`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/repository-structure.md` (if move rules differ)

- [ ] **Step 1: Write failing path validation**

```bash
#!/usr/bin/env bash
set -euo pipefail
test -d apps/api
test -d apps/web
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/test-paths.sh`  
Expected: FAIL before directory migration.

- [ ] **Step 3: Perform atomic moves and command-path updates**

- Move directories with git-aware commands.
- Update root scripts and make targets to use `apps/api` and `apps/web`.
- Explicitly exclude environment caches and generated dependency directories from move history (for example virtualenv and `node_modules`), then regenerate via bootstrap commands.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/test-paths.sh`  
Expected: PASS after migration.

- [ ] **Step 5: Controller commits task**

```bash
git add apps/api apps/web Makefile scripts
git commit -m "refactor(repo): [plan:2026-03-28-repository-structure-plan][task:T02] migrate to apps api/web layout"
```

**Anti-pattern avoidance notes:**
- No duplicate source trees left behind.
- No compatibility shims that mask broken paths.
- Keep path migration explicit and deterministic.

## Chunk 2: Backend/Frontend Boundary Implementation

### Task T03: Implement Backend Domain Module Layout

**Task ID:** `T03`  
**Commit Ownership:** Controller at task end (single commit)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/core/{config.py,logging.py,errors.py,deps.py}`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/knowledge/{api.py,service.py,repo.py,schema.py,model.py}`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/search/{api.py,service.py,schema.py}`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/shared/db/{base.py,session.py}`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/{unit,integration,contract}/.gitkeep`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/main.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/pyproject.toml` (add backend test dependency and test command support)
- Test: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/test_module_imports.py`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/repository-structure.md` (if boundary rules evolve)

- [ ] **Step 1: Write failing backend structure test**

```python
from pathlib import Path

def test_backend_module_layout():
    assert Path("src/modules/knowledge/api.py").exists()
    assert Path("src/modules/search/service.py").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/unit/test_module_imports.py -q`  
Expected: FAIL before file creation.

- [ ] **Step 3: Add module files and wire `main.py` minimally**

- Create module skeletons with explicit dependency direction (`api -> service -> repo`).
- Update backend manifest to include runnable test tooling (`pytest`) used by validation commands.
- Avoid placing domain business logic in `src/shared`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/unit/test_module_imports.py -q`  
Expected: PASS.

- [ ] **Step 5: Controller commits task**

```bash
git add apps/api/src apps/api/tests apps/api/pyproject.toml
git commit -m "feat(api): [plan:2026-03-28-repository-structure-plan][task:T03] add domain module skeleton"
```

**Anti-pattern avoidance notes:**
- No oversized shared module storing business logic.
- No circular dependency between modules.
- No silent exception swallowing in `service`/`repo` scaffolding.

### Task T04: Implement Frontend Feature-First Structure and HTTP Guardrails

**Task ID:** `T04`  
**Commit Ownership:** Controller at task end (single commit)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/app/{router.tsx,providers.tsx}`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/knowledge/{pages,components,hooks,services,types,utils}/.gitkeep`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/search/{pages,components,hooks,services,types,utils}/.gitkeep`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/shared/{ui,hooks,utils,config}/.gitkeep`
- Create: `/Users/mianqin/Code/knowledge/apps/web/vitest.config.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/eslint.config.js` (or Biome equivalent)
- Modify: `/Users/mianqin/Code/knowledge/apps/web/package.json` (add `test` script and test runner dependency)
- Test: `/Users/mianqin/Code/knowledge/apps/web/tests/integration/http-guardrail.spec.ts`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/repository-structure.md` (if guardrail semantics change)

- [ ] **Step 1: Write failing guardrail test**

```ts
import { readFileSync } from "node:fs";
import { test, expect } from "vitest";

test("no direct fetch/axios calls in features", () => {
  const content = readFileSync("src/features/knowledge/services/index.ts", "utf8");
  expect(content.includes("fetch(")).toBe(false);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && pnpm run test -- --run`  
Expected: FAIL while guardrails are not yet enforced.

- [ ] **Step 3: Create feature layout and enforce lint/static rule**

- Add feature-first tree.
- Add and configure web test runner (`vitest`) and `test` script in `package.json`.
- Add lint/static restriction preventing direct `fetch`/`axios` in feature service files.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && pnpm run test -- --run`  
Expected: PASS and lint guardrail active.

- [ ] **Step 5: Controller commits task**

```bash
git add apps/web/src apps/web/tests apps/web/eslint.config.js apps/web/package.json apps/web/vitest.config.ts
git commit -m "feat(web): [plan:2026-03-28-repository-structure-plan][task:T04] add feature structure and http guardrails"
```

**Anti-pattern avoidance notes:**
- No bypass path for direct ad hoc HTTP calls.
- No duplicated API URL construction logic across features.
- No silent network error swallowing in service wrappers.

## Chunk 3: Contracts, Infra, CI, and Verification

### Task T05: Create Contract Package and Deterministic Generation Flow

**Task ID:** `T05`  
**Commit Ownership:** Controller at task end (single commit)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/packages/contracts/openapi/openapi.json`
- Create: `/Users/mianqin/Code/knowledge/packages/contracts/generated/{types.ts,client.ts}`
- Create: `/Users/mianqin/Code/knowledge/packages/contracts/scripts/{export-openapi.sh,generate-types.sh,generate-client.sh,verify-up-to-date.sh}`
- Create: `/Users/mianqin/Code/knowledge/packages/contracts/package.json`
- Create: `/Users/mianqin/Code/knowledge/packages/contracts/README.md`
- Modify: `/Users/mianqin/Code/knowledge/Makefile`
- Test: `/Users/mianqin/Code/knowledge/packages/contracts/scripts/test-contract-drift.sh`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/repository-structure.md` (if artifact policy changes)

- [ ] **Step 1: Write failing drift check**

```bash
#!/usr/bin/env bash
set -euo pipefail
make contracts-check
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash packages/contracts/scripts/test-contract-drift.sh`  
Expected: FAIL before scripts and artifacts exist.

- [ ] **Step 3: Implement export/generation/check scripts and wire Make targets**

- Export backend OpenAPI snapshot from `apps/api` into `packages/contracts/openapi/openapi.json`.
- Generate `generated/types.ts` and `generated/client.ts`.
- Fail fast on drift.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash packages/contracts/scripts/test-contract-drift.sh`  
Expected: PASS with zero drift.

- [ ] **Step 5: Controller commits task**

```bash
git add packages/contracts Makefile
git commit -m "feat(contracts): [plan:2026-03-28-repository-structure-plan][task:T05] add openapi-driven generation pipeline"
```

**Anti-pattern avoidance notes:**
- No manual one-off generation process.
- No partial update of types without client (or inverse) unless explicitly designed.
- No hidden script behavior; all failures are explicit.

### Task T06: Add Containerized Infra and Environment Layering

**Task ID:** `T06`  
**Commit Ownership:** Controller at task end (single commit)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/infra/compose/{docker-compose.dev.yml,docker-compose.prod.yml}`
- Create: `/Users/mianqin/Code/knowledge/infra/env/{api.dev.env.example,api.prod.env.example,web.dev.env.example,web.prod.env.example}`
- Create: `/Users/mianqin/Code/knowledge/apps/api/Dockerfile`
- Create: `/Users/mianqin/Code/knowledge/apps/web/Dockerfile`
- Modify: `/Users/mianqin/Code/knowledge/scripts/dev-up.sh`
- Modify: `/Users/mianqin/Code/knowledge/scripts/dev-down.sh`
- Test: `/Users/mianqin/Code/knowledge/scripts/test-compose-config.sh`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/repository-structure.md` (if infra boundary details change)

- [ ] **Step 1: Write failing compose config test**

```bash
#!/usr/bin/env bash
set -euo pipefail
docker compose -f infra/compose/docker-compose.dev.yml config >/dev/null
docker compose -f infra/compose/docker-compose.prod.yml config >/dev/null
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/test-compose-config.sh`  
Expected: FAIL before compose files are created.

- [ ] **Step 3: Add compose, env templates, and app Dockerfiles**

- Keep application business logic out of `infra/`.
- Keep environment files as templates only.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/test-compose-config.sh`  
Expected: PASS with valid compose manifests.

- [ ] **Step 5: Controller commits task**

```bash
git add infra apps/api/Dockerfile apps/web/Dockerfile scripts/dev-up.sh scripts/dev-down.sh
git commit -m "chore(infra): [plan:2026-03-28-repository-structure-plan][task:T06] add containerized compose and env layering"
```

**Anti-pattern avoidance notes:**
- No runtime behavior hidden in shell scripts.
- No app logic added under `infra/`.
- No production defaults silently reused for development.

### Task T07: Implement CI Quality Gates for Contracts and Structure Rules

**Task ID:** `T07`  
**Commit Ownership:** Controller at task end (single commit)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/.github/workflows/ci.yml`
- Modify: `/Users/mianqin/Code/knowledge/Makefile`
- Modify: `/Users/mianqin/Code/knowledge/scripts/check-all.sh`
- Test: `/Users/mianqin/Code/knowledge/scripts/test-ci-local.sh`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/repository-structure.md` (if gate policy changes)

- [ ] **Step 1: Write failing local CI parity test**

```bash
#!/usr/bin/env bash
set -euo pipefail
make check
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/test-ci-local.sh`  
Expected: FAIL before workflow and checks are fully wired.

- [ ] **Step 3: Add CI workflow and wire gates**

- Ensure CI uses root-level commands only.
- Include contract drift checks and application test/build checks.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash scripts/test-ci-local.sh`  
Expected: PASS locally with same commands used by CI workflow.

- [ ] **Step 5: Controller commits task**

```bash
git add .github/workflows/ci.yml Makefile scripts/check-all.sh scripts/test-ci-local.sh
git commit -m "ci(repo): [plan:2026-03-28-repository-structure-plan][task:T07] enforce monorepo quality gates"
```

**Anti-pattern avoidance notes:**
- No CI-only hidden steps that differ from local checks.
- No silent skip for contract drift or boundary enforcement.
- No duplicated gate definitions across scripts and workflow.

## Plan Coverage Gate

| Design Commitment | Task IDs | Files | Tests | Spec Updates | Planned Commit Message |
|---|---|---|---|---|---|
| Strong governance top-level structure (`apps/*`, `packages/*`, `infra`, `scripts`, `Makefile`) | T01, T02 | `Makefile`, `scripts/*`, moved `apps/*` paths | `scripts/test-smoke.sh`, `scripts/test-paths.sh` | Design only if path decisions change | `chore(repo)...T01`, `refactor(repo)...T02` |
| Backend domain-oriented module layout (`knowledge`, `search`) | T03 | `apps/api/src/modules/*`, `apps/api/src/core/*`, `apps/api/src/shared/*` | `apps/api/tests/unit/test_module_imports.py` | Design only if module boundary policy changes | `feat(api)...T03` |
| Frontend feature-first layout with generated-client-only HTTP access | T04 | `apps/web/src/features/*`, `apps/web/src/shared/*`, lint config | `apps/web/tests/integration/http-guardrail.spec.ts` | Design only if guardrail semantics change | `feat(web)...T04` |
| Contract package with versioned OpenAPI + generated artifacts | T05 | `packages/contracts/openapi/*`, `packages/contracts/generated/*`, scripts | `packages/contracts/scripts/test-contract-drift.sh` | Design only if artifact policy changes | `feat(contracts)...T05` |
| Containerized infra and environment layering | T06 | `infra/compose/*`, `infra/env/*`, app Dockerfiles | `scripts/test-compose-config.sh` | Design only if infra boundary policy changes | `chore(infra)...T06` |
| CI/local parity and deterministic quality gates | T07 | `.github/workflows/ci.yml`, `scripts/check-all.sh`, `Makefile` | `scripts/test-ci-local.sh` | Design only if validation contract changes | `ci(repo)...T07` |

Coverage self-check results:
- All design commitments are mapped to concrete tasks, files, tests, and commit ownership.
- No uncovered behavior-changing deltas are present.
- Every task includes one controller-owned commit step.
- Tasks explicitly avoid workaround-only behavior, silent failures, over-defensive logic, and unnecessary duplication.

Plan complete and saved to `/Users/mianqin/Code/knowledge/.orbital/specs/plans/2026-03-28-repository-structure-plan.md`. Ready to execute?

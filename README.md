# Knowledge Monorepo

This repository is governed from the root with `Makefile` and `scripts/`.

## Root Commands

- `make bootstrap`: install and sync dependencies.
- `make dev-up`: start development runtime (Docker Compose dev stack).
- `make dev-down`: stop development runtime.
- `make contracts`: export and generate API contracts.
- `make contracts-check`: verify contract artifacts are up to date.
- `make test`: run backend and frontend tests.
- `make check`: run contract verification and tests.

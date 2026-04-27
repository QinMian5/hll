.DEFAULT_GOAL := help

.PHONY: help bootstrap dev-up dev-down prod-up prod-down test-db-up test-db-down fix test check integration alembic-autogen alembic-upgrade-dev alembic-upgrade-test alembic-upgrade-prod

help:
	@printf '%s\n' \
		'Available commands:' \
		'  make bootstrap             Initialize repository dependencies and local tools' \
		'  make dev-up                Start local development services' \
		'  make dev-down              Stop local development services' \
		'  make prod-up               Start local production-like services' \
		'  make prod-down             Stop local production-like services' \
		'  make test-db-up            Start isolated test database services' \
		'  make test-db-down          Stop isolated test database services' \
		'  make fix                   Apply safe repository-wide auto-fixes' \
		'  make test                  Run the default fast test suite' \
		'  make check                 Run the pre-submit aggregate checks' \
		'  make integration           Run the heavier integration test flow' \
		'  make alembic-autogen APP=api MSG="..." Generate an app Alembic migration' \
		'  make alembic-upgrade-dev   Apply all app migrations to development databases' \
		'  make alembic-upgrade-test  Apply all app migrations to test databases' \
		'  make alembic-upgrade-prod  Apply all app migrations to production databases'

bootstrap:
	bash scripts/bootstrap.sh

dev-up:
	bash scripts/dev-up.sh

dev-down:
	bash scripts/dev-down.sh $(ARGS)

prod-up:
	bash scripts/prod-up.sh

prod-down:
	bash scripts/prod-down.sh

test-db-up:
	bash scripts/test-db-up.sh

test-db-down:
	bash scripts/test-db-down.sh $(ARGS)

fix:
	uv run --project apps/api ruff check --fix apps/api/src
	uv run --project apps/api ruff format apps/api/src
	uv run --project apps/mcp ruff check --fix apps/mcp/src apps/mcp/tests
	uv run --project apps/mcp ruff format apps/mcp/src apps/mcp/tests
	pnpm run js:fix

test:
	bash scripts/run-tests.sh

check:
	bash scripts/check-all.sh

integration:
	bash scripts/test-integration.sh

alembic-autogen:
	bash scripts/alembic-autogen.sh

alembic-upgrade-dev:
	bash scripts/alembic-upgrade-dev.sh

alembic-upgrade-test:
	bash scripts/alembic-upgrade-test.sh

alembic-upgrade-prod:
	bash scripts/alembic-upgrade-prod.sh

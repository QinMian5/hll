.PHONY: bootstrap dev-up dev-down prod-up prod-down test-db-up test-db-down test-integration format fix lint typecheck contracts contracts-check test check alembic-autogen alembic-upgrade-dev alembic-upgrade-test alembic-upgrade-prod

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

test-integration:
	bash scripts/test-integration.sh

format:
	uvx ruff format apps/api/src
	pnpm --dir apps/web run format

fix:
	uvx ruff check --fix apps/api/src
	uvx ruff format apps/api/src
	pnpm --dir apps/web run fix

lint:
	bash scripts/lint.sh

typecheck:
	bash scripts/typecheck.sh

contracts:
	bash scripts/contracts.sh

contracts-check:
	bash scripts/contracts-check.sh

test:
	bash scripts/run-tests.sh

check:
	bash scripts/check-all.sh

alembic-autogen:
	bash scripts/alembic-autogen.sh

alembic-upgrade-dev:
	bash scripts/alembic-upgrade-dev.sh

alembic-upgrade-test:
	bash scripts/alembic-upgrade-test.sh

alembic-upgrade-prod:
	bash scripts/alembic-upgrade-prod.sh

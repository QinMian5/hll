.PHONY: bootstrap dev-up dev-down prod-up prod-down format fix lint typecheck contracts contracts-check test check

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

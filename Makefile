.PHONY: bootstrap dev down api web contracts contracts-check test check

bootstrap:
	bash scripts/bootstrap.sh

dev:
	bash scripts/dev-up.sh

down:
	bash scripts/dev-down.sh

api:
	bash scripts/run-api.sh

web:
	bash scripts/run-web.sh

contracts:
	bash scripts/contracts.sh

contracts-check:
	bash scripts/contracts-check.sh

test:
	bash scripts/run-tests.sh

check:
	bash scripts/check-all.sh

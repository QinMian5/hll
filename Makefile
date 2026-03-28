.PHONY: bootstrap dev-up dev-down contracts contracts-check test check

bootstrap:
	bash scripts/bootstrap.sh

dev-up:
	bash scripts/dev-up.sh

dev-down:
	bash scripts/dev-down.sh

contracts:
	bash scripts/contracts.sh

contracts-check:
	bash scripts/contracts-check.sh

test:
	bash scripts/run-tests.sh

check:
	bash scripts/check-all.sh

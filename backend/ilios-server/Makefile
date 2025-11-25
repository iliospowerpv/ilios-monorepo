.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open(sys.argv[1])
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: black
black: ## check style with black
	black . --diff --check


.PHONY: lint
lint: ## check style with flake8
	flake8 app locust_tests --statistics --count


.PHONY: test
test: ## run tests quickly with the default Python
	pytest -vv


.PHONY: check
check: ## run black, flake8 and pytest all together
	$(MAKE) black lint test


.PHONY: run
run: ## start FastAPI application and open it in the browser
	@echo "Starting the app . . ."
	$(BROWSER) http://127.0.0.1:8000/docs
	uvicorn app.main:app --reload --port 8000 --log-config=log_conf.yaml

.PHONY: up-patch
up-patch: ## update patch version
	bump2version patch --allow-dirty

.PHONY: up-minor
up-minor: ## update minor version
	bump2version minor --allow-dirty

.PHONY: up-major
up-major: ## update major version
	bump2version major --allow-dirty

.PHONY: notes
notes: ## create release notes as comparison latest 'develop' and 'main' branches
	python dev_scripts/collect_release_notes.py

.PHONY: validate-migrations
validate-migrations: ## validate migrations order
	python dev_scripts/validate_migration_order.py

.PHONY: generate-permissions
generate-permissions: ## create list of role permissions change for migration
	python dev_scripts/create_permission_updates.py

.PHONY: locust
locust: ## start Locust server and open it in the browser
	@echo "Starting Locust UI . . ."
	$(BROWSER) http://127.0.0.1:8089
	locust -f locust_tests/locustfile.py

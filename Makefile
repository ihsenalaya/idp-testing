.PHONY: help validate-openapi validate-yaml microcks-contract-test lint-shell py-compile \
        test-unit test-regression test-migration test-contract test-e2e test-all \
        seed pr-comment

MICROCKS_URL        ?= http://localhost:8080
BACKEND_URL         ?= http://localhost:8080
FRONTEND_URL        ?= http://localhost:3000
API_NAME            ?= Preview Catalog API
API_VERSION         ?= 1.0.0
TEST_RUNNER         ?= OPEN_API_SCHEMA
REPORT_DIR          ?= ./test-reports
PR                  ?=
PREVIEW_URL         ?=
NAMESPACE           ?=

help:
	@echo ""
	@echo "  idp-testing — available make targets"
	@echo ""
	@echo "  Tests"
	@echo "    test-unit       Run pure unit tests (no DB, no server)"
	@echo "    test-regression Run regression tests (requires DATABASE_URL)"
	@echo "    test-migration  Run Alembic migration up/down tests (requires DATABASE_URL)"
	@echo "    test-contract   Run schemathesis contract tests (requires APP_URL)"
	@echo "    test-e2e        Run Playwright E2E tests (requires FRONTEND_URL)"
	@echo "    test-all        Run all test categories"
	@echo ""
	@echo "  Data"
	@echo "    seed            Load default seed data (requires DATABASE_URL)"
	@echo ""
	@echo "  Tooling"
	@echo "    validate-openapi       Validate api/openapi.yaml"
	@echo "    validate-yaml          Validate all YAML files"
	@echo "    microcks-contract-test Run Microcks contract test"
	@echo "    lint-shell             Run shellcheck on shell scripts"
	@echo "    py-compile             Syntax-check all Python files"
	@echo "    pr-comment             Build the PR comment (set PR, PREVIEW_URL, NAMESPACE)"
	@echo ""
	@echo "  Env vars:"
	@echo "    DATABASE_URL   PostgreSQL connection string"
	@echo "    APP_URL        Running backend URL (default: $(BACKEND_URL))"
	@echo "    FRONTEND_URL   Running frontend URL (default: $(FRONTEND_URL))"
	@echo ""

# ── Test targets ──────────────────────────────────────────────────────────────

test-unit:
	@echo "→ Unit tests (no DB required) …"
	@mkdir -p $(REPORT_DIR)
	@python3 -m pytest tests/unit/ -v --tb=short \
	  --json-report --json-report-file=$(REPORT_DIR)/pytest-unit.json

test-regression:
	@echo "→ Regression tests (requires DATABASE_URL) …"
	@mkdir -p $(REPORT_DIR)
	@python3 -m pytest tests/regression/ -v --tb=short \
	  --json-report --json-report-file=$(REPORT_DIR)/pytest-regression.json

test-migration:
	@echo "→ Migration tests (requires DATABASE_URL) …"
	@mkdir -p $(REPORT_DIR)
	@python3 -m pytest tests/migration/ -v --tb=short \
	  --json-report --json-report-file=$(REPORT_DIR)/pytest-migration.json

test-contract:
	@echo "→ Contract tests (requires APP_URL=$(BACKEND_URL)) …"
	@mkdir -p $(REPORT_DIR)
	@APP_URL="$(BACKEND_URL)" python3 -m pytest tests/contract/ -v --tb=short \
	  --json-report --json-report-file=$(REPORT_DIR)/pytest-contract.json

test-e2e:
	@echo "→ E2E tests (requires FRONTEND_URL=$(FRONTEND_URL)) …"
	@mkdir -p $(REPORT_DIR)
	@FRONTEND_URL="$(FRONTEND_URL)" APP_URL="$(BACKEND_URL)" \
	  python3 tests/e2e.py 2>&1 | tee $(REPORT_DIR)/e2e.log

test-all: test-unit test-regression test-migration test-contract
	@echo "→ All test suites complete."
	@echo "   Reports saved to $(REPORT_DIR)/"

# ── Data ──────────────────────────────────────────────────────────────────────

seed:
	@if [ -z "$(DATABASE_URL)" ]; then echo "ERROR: DATABASE_URL is not set"; exit 1; fi
	@echo "→ Loading default seed data …"
	@psql "$(DATABASE_URL)" -f seeds/default/seed.sql
	@echo "   Seed complete."

# ── PR Comment Builder ────────────────────────────────────────────────────────

pr-comment:
	@echo "→ Building PR comment …"
	@mkdir -p $(REPORT_DIR)
	@python3 -m tools.pr-comment-builder \
	  --report-dir $(REPORT_DIR) \
	  --preview-url "$(PREVIEW_URL)" \
	  --namespace "$(NAMESPACE)" \
	  --pr "$(PR)"

# ── Validation ────────────────────────────────────────────────────────────────

validate-openapi:
	@echo "→ Validating api/openapi.yaml …"
	@python3 scripts/validate-openapi.py api/openapi.yaml

validate-yaml:
	@echo "→ Validating YAML files …"
	@python3 scripts/validate-yaml.py

microcks-contract-test:
	@echo "→ Running Microcks contract test …"
	@MICROCKS_URL="$(MICROCKS_URL)" \
	 BACKEND_URL="$(BACKEND_URL)" \
	 API_NAME="$(API_NAME)" \
	 API_VERSION="$(API_VERSION)" \
	 TEST_RUNNER="$(TEST_RUNNER)" \
	 bash scripts/run-microcks-contract-test.sh

lint-shell:
	@echo "→ Running shellcheck …"
	@if command -v shellcheck >/dev/null 2>&1; then \
	  shellcheck scripts/run-microcks-contract-test.sh; \
	  echo "  shellcheck passed."; \
	else \
	  echo "  shellcheck not installed — skipping."; \
	fi

py-compile:
	@echo "→ Syntax-checking Python files …"
	@python3 -m py_compile app.py && echo "  PASS app.py"
	@python3 -m py_compile frontend.py && echo "  PASS frontend.py"
	@python3 -m py_compile tests/regression.py && echo "  PASS tests/regression.py"
	@python3 -m py_compile tests/e2e.py && echo "  PASS tests/e2e.py"
	@python3 -m py_compile tests/example_test.py && echo "  PASS tests/example_test.py"
	@python3 -m py_compile scripts/validate-yaml.py && echo "  PASS scripts/validate-yaml.py"
	@python3 -m py_compile scripts/validate-openapi.py && echo "  PASS scripts/validate-openapi.py"

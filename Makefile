# cloud-platform-skills — every gate, one entrypoint.
# All gates are stdlib-only Python 3.10+; `make check` needs no install step.

PYTHON ?= python3

# Single source of truth for the ruff pin: CI runs `make lint`, so there is no second
# copy of this version to drift. Node lint tools are pinned in package.json for the same reason.
RUFF_VERSION ?= 0.16.3
MIN_PASS_RATE ?= 95

.DEFAULT_GOAL := help
.PHONY: help check validate evals compliance workflows sync docs sync-check docs-check \
        compile release-check manifest bump secrets-baseline scan hooks clean ci \
        lint lint-md lint-md-fix lint-py format format-check fix

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'

## ---------------------------------------------------------------- gates

check: validate evals compliance workflows sync-check docs-check compile ## Run every gate (what CI runs)
	@echo "note: run 'make lint' too — it needs node + ruff, which the gates deliberately do not"
	@echo ""
	@echo "all gates passed"

validate: ## Structure, frontmatter, cross-references, mirror sync
	$(PYTHON) scripts/validate-skills.py --check-sync --strict

evals: ## Routing + content-coverage evals
	$(PYTHON) scripts/run-evals.py --min-pass-rate $(MIN_PASS_RATE)

compliance: ## 8-point compliance gate (agent safety, secrets, accuracy)
	$(PYTHON) scripts/compliance-check.py

workflows: ## GitHub Actions security audit
	$(PYTHON) scripts/audit-workflows.py

sync-check: ## Fail if generated runtime targets are stale
	$(PYTHON) scripts/sync-all.py --check

docs-check: ## Fail if generated documentation is stale
	$(PYTHON) scripts/generate-docs.py --check

compile: ## Byte-compile all Python
	$(PYTHON) -m compileall -q scripts
	@find skills -name '*.py' -print0 | xargs -0 -r $(PYTHON) -m py_compile

## ---------------------------------------------------------------- lint

lint: lint-md format-check lint-py ## Run every linter (markdownlint + prettier + ruff)

node_modules: package.json package-lock.json  ## Install the pinned lint toolchain
	npm ci
	@touch node_modules

lint-md: node_modules ## markdownlint over the authored markdown surface
	npm run lint:check

lint-md-fix: node_modules ## markdownlint with autofix
	npm run lint:fix

format: node_modules ## prettier write (JSON, JSONC, YAML — markdown is markdownlint's)
	npm run format

format-check: node_modules ## prettier check
	npm run format:check

fix: node_modules .venv-lint ## markdownlint --fix + prettier --write + ruff format
	npm run fix
	.venv-lint/bin/ruff check --fix scripts
	.venv-lint/bin/ruff format scripts

# A repo-local venv, not a bare `pip install`: on Homebrew/Debian Pythons PEP 668 refuses to
# install into the system interpreter, and `--break-system-packages` is not something a lint
# target should do to a developer's machine. This keeps `make lint` working identically on a
# laptop and on a CI runner.
.venv-lint: Makefile  ## Install the pinned ruff into a repo-local venv
	@$(PYTHON) -m venv .venv-lint
	@.venv-lint/bin/pip install --quiet --upgrade pip
	@.venv-lint/bin/pip install --quiet ruff==$(RUFF_VERSION)
	@touch .venv-lint

lint-py: .venv-lint ## ruff lint + format check over scripts/
	.venv-lint/bin/ruff check scripts
	.venv-lint/bin/ruff format --check scripts

format-py: .venv-lint ## ruff format (write) over scripts/
	.venv-lint/bin/ruff format scripts

## ---------------------------------------------------------------- generate

sync: ## Regenerate every runtime target from skills/
	$(PYTHON) scripts/sync-all.py

docs: ## Regenerate the documentation site sources
	$(PYTHON) scripts/generate-docs.py

serve: docs ## Serve the documentation site locally
	@$(PYTHON) -m pip install -q -r requirements-dev.txt && mkdocs serve

## ---------------------------------------------------------------- release

release-check: ## Verify tag/plugin.json/CHANGELOG agreement (VERSION=x.y.z)
	@test -n "$(VERSION)" || (echo "usage: make release-check VERSION=1.0.1"; exit 2)
	$(PYTHON) scripts/check-release.py --version $(VERSION)

manifest: ## Write the release skill inventory
	$(PYTHON) scripts/check-release.py --manifest skills-manifest.json

bump: ## Set every plugin.json to VERSION=x.y.z
	@test -n "$(VERSION)" || (echo "usage: make bump VERSION=1.0.1"; exit 2)
	$(PYTHON) scripts/check-release.py --bump $(VERSION)

## ---------------------------------------------------------------- security

scan: compliance workflows ## Local security pass (skill content + CI posture)
	@command -v gitleaks >/dev/null 2>&1 \
	  && gitleaks detect --config .gitleaks.toml --redact --verbose \
	  || echo "note: gitleaks not installed locally — CI runs it (see .github/workflows/security.yml)"

secrets-baseline: ## Create/refresh the detect-secrets baseline for pre-commit
	@command -v detect-secrets >/dev/null 2>&1 || (echo "pip install detect-secrets"; exit 2)
	detect-secrets scan \
	  --exclude-files '^(docs/|\.claude/skills/|\.agents/skills/|\.cursor/rules/|\.gitleaks\.toml|scripts/compliance-check\.py|package-lock\.json)' \
	  > .secrets.baseline
	@echo "wrote .secrets.baseline — review it before committing"

hooks: ## Install pre-commit hooks
	@command -v pre-commit >/dev/null 2>&1 || (echo "pip install pre-commit"; exit 2)
	pre-commit install
	pre-commit run --all-files || true

## ---------------------------------------------------------------- misc

ci: check ## Alias for check
clean: ## Remove generated reports and caches
	rm -f benchmark.json compliance.json workflow-audit.json skills-manifest.json release-notes.md
	rm -rf site .cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +

# ──────────────────────────────────────────────────────────────────────
# Amazon Bedrock AgentCore — Employee Onboarding Sample
# ──────────────────────────────────────────────────────────────────────
# Run `make` or `make help` to see available targets.

# Use Bash for `source` compatibility on macOS and Amazon Linux 2023
SHELL := /bin/bash

# ── Virtual-environment paths ────────────────────────────────────────
VENV         := src/.venv
VENV_ACTIVATE := $(VENV)/bin/activate

# ── User-overridable variables ───────────────────────────────────────
MODEL  ?=
PROMPT ?= onboard jane doe as product manager

# ── Venv existence guard ─────────────────────────────────────────────
# Targets that require the venv call $(check_venv) as their first recipe line.
define check_venv
	@if [ ! -f $(VENV_ACTIVATE) ]; then \
		echo "Error: Virtual environment not found. Please run 'make deploy' first."; \
		exit 1; \
	fi
endef

# ── Phony declarations ──────────────────────────────────────────────
.PHONY: help deploy test smoke-test cli clean verify-clean

# ── Targets ─────────────────────────────────────────────────────────

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

deploy: ## Deploy the full sample to AWS (accepts MODEL=<model-id>)
	@chmod +x scripts/deploy.sh
	@if [ -n "$(MODEL)" ]; then ./scripts/deploy.sh --model "$(MODEL)"; else ./scripts/deploy.sh; fi

test: ## Run the full test suite (pytest)
	$(check_venv)
	@source $(VENV_ACTIVATE) && pip install --quiet -r src/agentcore/requirements.txt pytest hypothesis && pytest tests/ -v

smoke-test: ## Run a curl-based smoke test against the deployed agent
	@chmod +x scripts/test_agentcore_curl.sh
	@./scripts/test_agentcore_curl.sh "$(PROMPT)"

cli: ## Invoke the CLI client with an onboarding prompt
	$(check_venv)
	@source $(VENV_ACTIVATE) && python3 src/cli/onboarding_cli.py "$(PROMPT)"

clean: ## Tear down all AWS resources
	@chmod +x scripts/complete_cleanup.sh
	@./scripts/complete_cleanup.sh

verify-clean: ## Verify that all AWS resources have been removed
	$(check_venv)
	@source $(VENV_ACTIVATE) && python3 scripts/verify_cleanup.py

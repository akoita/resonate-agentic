# Resonate Agentic — developer harness entrypoints.
# Lean by design: every target maps to a phase of the agentic SDLC.

PY ?= python
VENV := .venv

.DEFAULT_GOAL := help
.PHONY: help install lint fmt test guardrails check run web eval deploy clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime + dev deps
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install pytest pytest-asyncio respx ruff

lint: ## Static analysis (ruff)
	$(PY) -m ruff check app tests

fmt: ## Auto-format / autofix
	$(PY) -m ruff check --fix app tests

test: ## Run the offline test suite
	$(PY) -m pytest -q

guardrails: ## Enforce AGENTS.md hard rules (deterministic)
	$(PY) scripts/harness_guardrails.py

check: lint test guardrails ## The pre-PR gate: lint + test + guardrails

run: ## Run the agent in the terminal (ADK)
	adk run app

web: ## Run the ADK browser playground
	adk web app

eval: ## Run agent evals (see .claude/skills/eval-and-deploy)
	@echo "Eval harness not yet wired — see ROADMAP.md (Phase 2) and the eval-and-deploy skill."

deploy: ## Deploy intent → private IaC repo (ADR-0005); cloud CD lives in resonate-agentic-iac
	@echo "Deployment is owned by the private control plane: akoita/resonate-agentic-iac (ADR-0005)."
	@echo "Trigger via the 'Deploy Dispatch' workflow (sends repository_dispatch); prod is manual-only."

clean: ## Remove caches
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

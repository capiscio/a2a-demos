.PHONY: dev install clean test lint enforcement-demo policy-demo multi-agent-demo help

# ═══════════════════════════════════════════════════════════════
# A2A Demos — Development Makefile
# ═══════════════════════════════════════════════════════════════
#
# Two modes:
#   make dev      — Install from LOCAL repos (pre-release testing)
#   make install  — Install from PyPI (released versions)
#
# After switching modes, run the individual demo targets.

SHELL := /bin/bash
PYTHON := python3
LOCAL_DEPS := requirements-local.txt

# Paths to local sibling repos (relative to this Makefile)
SDK_REPO     := ../capiscio-sdk-python
MCP_REPO     := ../capiscio-mcp-python
LC_REPO      := ../langchain-capiscio

help: ## Show this help
	@echo "╔══════════════════════════════════════════════════════════╗"
	@echo "║  a2a-demos Makefile                                      ║"
	@echo "╠══════════════════════════════════════════════════════════╣"
	@echo "║  Development (local repos):                              ║"
	@echo "║    make dev          Install all deps from local repos   ║"
	@echo "║    make dev-check    Verify local repos exist            ║"
	@echo "║                                                          ║"
	@echo "║  Release (PyPI):                                         ║"
	@echo "║    make install      Install all deps from PyPI          ║"
	@echo "║                                                          ║"
	@echo "║  Demos:                                                  ║"
	@echo "║    make enforcement-demo  Run Enforcement Demo             ║"
	@echo "║    make multi-agent-demo  Run Multi-Agent Demo              ║"
	@echo "║                                                          ║"
	@echo "║  Quality:                                                ║"
	@echo "║    make lint         Lint all Python files                ║"
	@echo "║    make test         Syntax-check all Python files        ║"
	@echo "║    make clean        Remove venvs and caches             ║"
	@echo "╚══════════════════════════════════════════════════════════╝"

# ─── Development mode (local repos) ─────────────────────────────────────

dev-check: ## Verify local dependency repos exist
	@echo "Checking local repos..."
	@test -f $(SDK_REPO)/pyproject.toml || (echo "❌ $(SDK_REPO) not found"; exit 1)
	@test -f $(MCP_REPO)/pyproject.toml || (echo "❌ $(MCP_REPO) not found"; exit 1)
	@test -f $(LC_REPO)/pyproject.toml  || (echo "❌ $(LC_REPO) not found"; exit 1)
	@echo "✓ capiscio-sdk-python: $$(grep 'version' $(SDK_REPO)/pyproject.toml | head -1)"
	@echo "✓ capiscio-mcp-python: $$(grep 'version' $(MCP_REPO)/pyproject.toml | head -1)"
	@echo "✓ langchain-capiscio:  $$(grep 'version' $(LC_REPO)/pyproject.toml | head -1)"

dev: dev-check ## Install ALL demos using local repos (pre-release testing)
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  Installing from LOCAL repos (dev mode)"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	# Shared event emitter
	$(PYTHON) -m pip install -e multi-agent-demo/shared/ -q
	# Local CapiscIO packages (overrides any PyPI versions)
	$(PYTHON) -m pip install -r $(LOCAL_DEPS)
	# Per-demo dependencies (non-capiscio deps like dotenv, httpx)
	$(PYTHON) -m pip install python-dotenv httpx uvicorn fastapi -q
	# Enforcement Demo
	cd enforcement-demo && $(PYTHON) -m pip install -r requirements.txt --no-deps -q 2>/dev/null || true
	# Agent frameworks
	$(PYTHON) -m pip install langchain langchain-openai langchain-community langgraph -q
	$(PYTHON) -m pip install "crewai>=1.12.0,<2.0.0" "crewai-tools>=1.12.0,<2.0.0" -q
	@echo ""
	@echo "✅ Dev mode active. Local package versions:"
	@$(PYTHON) -m pip show capiscio-sdk 2>/dev/null | grep -E "^(Name|Version|Location)"
	@$(PYTHON) -m pip show capiscio-mcp 2>/dev/null | grep -E "^(Name|Version|Location)"
	@$(PYTHON) -m pip show langchain-capiscio 2>/dev/null | grep -E "^(Name|Version|Location)"
	@echo ""
	@echo "💡 Editable installs — changes in local repos take effect immediately."

# ─── Release mode (PyPI) ────────────────────────────────────────────────

install: ## Install ALL demos from PyPI (released versions)
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  Installing from PyPI (release mode)"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	$(PYTHON) -m pip install -e multi-agent-demo/shared/ -q
	cd enforcement-demo && $(PYTHON) -m pip install -r requirements.txt -q
	cd policy-demo && $(PYTHON) -m pip install -r requirements.txt -q
	@for agent in langchain-agent crewai-agent langgraph-agent; do \
		echo "  Installing multi-agent-demo/agents/$$agent..."; \
		cd multi-agent-demo/agents/$$agent && $(PYTHON) -m pip install -r requirements.txt -q && cd ../../..; \
	done
	@echo ""
	@echo "✅ Release mode active. PyPI versions:"
	@$(PYTHON) -m pip show capiscio-sdk 2>/dev/null | grep -E "^(Name|Version)"
	@$(PYTHON) -m pip show capiscio-mcp 2>/dev/null | grep -E "^(Name|Version)"
	@$(PYTHON) -m pip show langchain-capiscio 2>/dev/null | grep -E "^(Name|Version)"

# ─── Demo runners ───────────────────────────────────────────────────────

enforcement-demo: ## Run Enforcement Demo — Zero to Enforcement
	cd enforcement-demo && $(PYTHON) run_demo.py

policy-demo: ## Run Policy Demo — Policy hot-swap scenarios
	cd policy-demo && $(PYTHON) run_demo.py

multi-agent-demo: ## Run Multi-Agent Demo — setup + run agents
	cd multi-agent-demo && ./setup.sh

# ─── Quality ─────────────────────────────────────────────────────────────

lint: ## Lint all Python files
	ruff check . --select E,F,W,I --ignore E501

test: ## Syntax-check all Python files
	find . -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" \
		-exec $(PYTHON) -m py_compile {} +
	@echo "✓ All Python files are syntactically valid"

clean: ## Remove venvs and caches
	rm -rf enforcement-demo/.venv
	rm -rf multi-agent-demo/agents/langchain-agent/.venv multi-agent-demo/agents/crewai-agent/.venv multi-agent-demo/agents/langgraph-agent/.venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned"

.PHONY: setup demo test lint build-web deploy deploy-pages clean

PYTHON := python3.12
VENV   := .venv
PIP    := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF   := $(VENV)/bin/ruff
GRAVEYARD := $(VENV)/bin/graveyard

# ── Setup ──────────────────────────────────────────────────────────────────────
setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo ""
	@echo "✓ Python env ready. Run: source $(VENV)/bin/activate"
	@if [ -d web ] && [ -f web/package.json ]; then \
	  cd web && npm ci && echo "✓ Node deps ready"; \
	fi

# ── Demo ───────────────────────────────────────────────────────────────────────
demo:
	$(GRAVEYARD) scan --demo --out /tmp/graveyard-demo.json
	@echo ""
	@echo "✓ Demo report written to /tmp/graveyard-demo.json"

# ── Demo-live: scan a moto-mocked account (no real AWS, fake creds only) ──────
demo-live:
	$(VENV)/bin/python scripts/moto_demo_scan.py --out /tmp/graveyard-live.json
	@echo ""
	@echo "✓ moto live-mode report written to /tmp/graveyard-live.json"
	@echo "  (fake credentials, in-process moto mock — no real AWS calls)"

# ── Tests ──────────────────────────────────────────────────────────────────────
test:
	$(PYTEST) tests/ -v
	@if [ -d web ] && [ -f web/package.json ]; then \
	  cd web && npx vitest run; \
	fi

# ── Lint ───────────────────────────────────────────────────────────────────────
lint:
	$(RUFF) check scanner/ tests/
	$(RUFF) format --check scanner/ tests/
	@if [ -d web ] && [ -f web/package.json ]; then \
	  cd web && npm run lint; \
	fi

# ── Web ────────────────────────────────────────────────────────────────────────
build-web:
	cd web && npm run build

# ── Deploy (Netlify — free, no AWS account needed) ────────────────────────────
deploy: build-web
	netlify deploy --prod --dir web/dist

# ── Deploy (GitHub Pages fallback — free, no AWS account needed) ──────────────
deploy-pages: build-web
	cd web && npx gh-pages -d dist

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	rm -rf $(VENV) __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

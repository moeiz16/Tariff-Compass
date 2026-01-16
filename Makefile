# Tariff Compass developer tasks. Everything runs offline: no Docker, no accounts, no keys.
# Ports: web 3050 · API 8050 (8051–8054 reserved). The Huey worker has no port.
# On small machines run heavy targets (setup, test, train, optimize, eval, web) one at a time.
PY      := backend/.venv/bin/python
BPY     := .venv/bin/python
NPM     := npm --prefix frontend
MANAGE  := cd backend && $(BPY) manage.py
LINT    := backend scripts $(wildcard eval)
ROUND   ?=
export MLFLOW_DISABLE_AGENT_HINT := 1

.PHONY: help setup setup-backend setup-ai setup-frontend lock api worker web web-dev dev migrate seed reset \
        fetch-data fixtures build-index train optimize eval test test-backend test-frontend lint format \
        typecheck smoke stop clean

help:            ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: setup-backend setup-frontend  ## Install API + web app, create .env, migrate and seed
	@test -f .env || cp .env.example .env
	$(MAKE) migrate
	-$(MAKE) seed

setup-backend:   ## Python 3.13 venv with the pinned lock (+ the package, editable)
	@if [ "$$(uname -s)" = "Darwin" ] && [ ! -f /opt/homebrew/opt/libomp/lib/libomp.dylib ] && [ ! -f /usr/local/opt/libomp/lib/libomp.dylib ]; then \
	  echo "LightGBM needs libomp on macOS: run 'brew install libomp' and re-run make setup."; exit 1; fi
	test -d backend/.venv || python3.13 -m venv backend/.venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r backend/requirements.lock
	$(PY) -m pip install -q --no-deps -e "backend[dev]"

setup-ai:        ## Optional: LiteLLM, only for LM providers other than Groq, Gemini and OpenRouter
	$(PY) -m pip install -q "litellm==1.109.1"

setup-frontend:  ## Install the web app (exact versions from package-lock.json)
	$(NPM) ci --no-audit --no-fund

lock:            ## Re-freeze backend/requirements.lock from the current venv (after changing pyproject pins)
	@{ echo "# Frozen from a clean Python 3.13 install of pyproject.toml core + dev dependencies (macOS arm64)."; \
	   echo "# Regenerate with: make lock"; \
	   $(PY) -m pip freeze --exclude-editable | grep -vi '^tariffcompass'; } > backend/requirements.lock

api:             ## API on :8050 (ASGI; SSE needs it)
	cd backend && $(BPY) -m uvicorn tariffcompass.asgi:application --host 127.0.0.1 --port 8050 --no-access-log

worker:          ## Huey worker (SQLite queue in data/huey.db): training rounds, index builds, exports, watch scans
	$(MANAGE) run_huey

web-dev:         ## SolidStart dev server on :3050 (proxies /api to :8050)
	$(NPM) run dev

web:             ## Production build of the web app, served on :3050
	$(NPM) run build && $(NPM) run start

dev:             ## API + worker + web dev server (Ctrl-C stops all)
	@$(MAKE) -j3 api worker web-dev

migrate:         ## Apply database migrations
	$(MANAGE) migrate -v0

seed:            ## Seed Northbound Goods Co. and Driftwood Customs Brokers (idempotent; TARIFF_COMPASS_DEMO_TODAY)
	$(MANAGE) seed

reset:           ## Delete the local database and indexes, re-anchor the demo clock, migrate and seed
	$(MANAGE) reset --yes

fetch-data:      ## Download rulings (~290 MB transfer, ~100 MB kept), the HTS and Canada's T2026 into data/
	$(PY) scripts/fetch_data.py

fixtures:        ## Rebuild the small committed sample fixtures from data/ (after fetch-data)
	$(PY) scripts/make_fixtures.py

build-index:     ## Build the search indexes over rulings and tariff text (data/index)
	$(MANAGE) build_index

train:           ## Train the classical first stage (TF-IDF linear models + LightGBM; tracked in mlruns/)
	$(MANAGE) train

optimize:        ## Run a GEPA training round (offline simulator unless LLM_FAKE=false + a key); ROUND=n
	$(MANAGE) optimize $(if $(ROUND),--round $(ROUND),)

eval:            ## Evaluation gates → eval/RESULTS.md (accuracy by depth, calibration, citations, landed cost, drift, latency)
	cd backend && $(BPY) ../eval/run.py

test: test-backend test-frontend  ## All tests

test-backend:    ## API, platform, search, classifier and duty tests (no servers needed)
	cd backend && $(BPY) -m pytest

test-frontend:   ## Web app type check, unit tests and production build
	$(NPM) run check && $(NPM) test && $(NPM) run build

lint:            ## Lint and format checks (ruff)
	$(PY) -m ruff check $(LINT)
	$(PY) -m ruff format --check $(LINT)

format:          ## Apply ruff formatting and safe fixes
	$(PY) -m ruff format $(LINT)
	$(PY) -m ruff check --fix $(LINT)

typecheck:       ## mypy (backend) + tsc (web)
	cd backend && $(BPY) -m mypy tariffcompass
	$(NPM) run check

smoke:           ## Re-verify the toolchain: DSPy + GEPA offline, Tantivy, scikit-learn, LightGBM, Optuna, MLflow, Huey
	cd backend && $(BPY) ../scripts/smoke/dspy_gepa_smoke.py
	cd backend && $(BPY) ../scripts/smoke/stack_smoke.py

stop:            ## Stop every Tariff Compass process started from this repo
	-pkill -f 'uvicorn tariffcompass.asgi' ; pkill -f 'manage.py run_huey' ; pkill -f 'vinxi dev --port 3050' ; \
	 pkill -f '.output/server/index.mjs' ; true
	@for p in 3050 8050 8051 8052 8053 8054; do lsof -ti :$$p >/dev/null 2>&1 && echo "port $$p still in use" || true; done

clean:           ## Remove caches and build output (keeps data/, mlruns/ and the venv)
	find $(LINT) -path '*/.venv' -prune -o -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .ruff_cache .mypy_cache .pytest_cache backend/.coverage backend/htmlcov frontend/.output frontend/.vinxi eval/out

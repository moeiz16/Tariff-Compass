# ADR 0001: Toolchain and data feasibility, verified on the target machine

**Status:** accepted

## Context

Tariff Compass must run on a laptop with 8 GB of RAM and limited disk, on Python 3.13 and Node 21.7.1, with no
Docker, no paid services and no local language model. Before writing the contract we installed every load-bearing
dependency and ran it, and we checked every data source for reachability, format and licence.

## What we checked and found

### Python (3.13.2, macOS arm64)

| Question | Result | Evidence |
|---|---|---|
| Django 5.x + Django Ninja on 3.13? | **Yes.** `Django==5.2.19` (LTS line; 6.x exists but the stack is Django 5) + `django-ninja==1.8.0` on `pydantic==2.14.3`. Ninja serialises with `by_alias` per operation, so `WireRouter` turns camelCase on for every route | `backend/tests/test_health.py`; API served on :8050 with uvicorn 0.54 (ASGI) |
| Huey with SQLite storage? | **Yes.** `huey==3.5.4`, `SqliteHuey` via `huey.contrib.djhuey`; `manage.py run_huey` processed a queued task end to end and updated its `Job` row. Tasks must live in an installed app's `tasks.py` (autodiscovery); a task defined elsewhere is "not found in TaskRegistry" | `scripts/smoke/stack_smoke.py`, `tests/test_jobs.py`, boot check |
| Tantivy Python bindings (BM25)? | **Yes.** `tantivy==0.27.0` ships an abi3 universal2 wheel; index build, `en_stem` tokenizer, BM25 search, stored fields and `SnippetGenerator` all work | `stack_smoke.py` (index + query in ~1 s cold) |
| DSPy, current version, and its weight? | **Yes, light.** `dspy==3.5.0` + `gepa==0.1.4`. Core dependencies are pure-Python utilities (pydantic, orjson, diskcache, json-repair, cloudpickle…). **No PyTorch, no LiteLLM, no OpenAI SDK** are pulled in; LiteLLM is an optional extra | `pip list` after install; full backend venv 571 MB |
| Does DSPy reach Groq / Gemini without LiteLLM? | **Yes.** DSPy 3.5 bundles its own provider client and resolves `groq/…`, `gemini/…` and `openrouter/…` natively; other prefixes (e.g. `cerebras/…`) still need LiteLLM, so `make setup-ai` installs it only for those | backend-selection probe on the installed package |
| Does `dspy.GEPA` run with a custom/fake LM and a reflection LM? | **Yes.** A custom DSPy *engine* (`complete(Request) → Response`) backs a `dspy.BaseLM`; GEPA ran with the same simulator as task LM and reflection LM, proposed new instructions from the metric's feedback, and lifted accuracy 0.00 → 1.00 on the smoke set in 0.1 s | `scripts/smoke/dspy_gepa_smoke.py` |
| Gotchas found while doing it | (1) DSPy 3.5's default adapter writes **XML-style field tags**; the chat adapter uses `[[ ## field ## ]]`; the JSON adapter is the fallback, and GEPA's reflection step is itself a DSPy predictor whose output field is `new_instruction`. The simulator therefore reads inputs and answers in whichever format the prompt asks for. (2) DSPy checks usage accounting: `total_tokens` must equal input + output | `adapters/lm_sim.py`, `tests/test_core_contracts.py` |
| LightGBM, scikit-learn, Optuna, MLflow (skinny)? | **Yes.** `lightgbm==4.7.0` (needs Homebrew `libomp`), `scikit-learn==1.9.1`, `optuna==5.0.0`, `mlflow-skinny==3.18.0` with a SQLite tracking store. TF-IDF → logistic regression, calibrated linear SVM, LightGBM multiclass with `pred_contrib` (per-feature contributions without the SHAP package), a 15-trial seeded Optuna study and an MLflow run all pass | `stack_smoke.py`: 34 s cold (mostly first imports), **peak 237 MB**; first-stage p95 0.23 ms on the toy set |
| Spec sheets and binder PDFs? | `pypdf==7.1.0` (text extraction), `reportlab==5.1.0` (binder PDF) | installed in the lock |

### Web (Node 21.7.1)

| Question | Result | Evidence |
|---|---|---|
| Newest SolidStart that builds on Node 21.7? | **SolidStart 1.5.1 on Vinxi 0.5.11 (Vite 6.4.6).** SolidStart 2.x needs Node ≥ 24 and Vite 8/9; `@solidjs/router` 1.x pairs with Start 2, so we pin `@solidjs/router@0.15.4` | `npm run build` (vinxi build) passes; `node .output/server/index.mjs` serves `/` with HTTP 200 on :3050 |
| Engine warnings? | npm prints EBADENGINE for Vite 6.4.6, nitropack 2.13.6, rolldown 1.2.19 and `@tanstack/router-utils` (they declare Node 20.19+/22.12+). Nothing in the build path fails on 21.7.1 | install log |
| Tailwind 4.1, components, tests? | `tailwindcss@4.1.18` + `@tailwindcss/vite@4.1.18` (peer Vite ^5.2–^7); Ark UI for Solid `@ark-ui/solid@5.40.0` with `tailwind-variants@4.0.2` recipes; `@tanstack/solid-table@8.21.3`; `vitest@3.2.7` (Vitest 4 needs Node 22); `typescript@5.9.3`. `tsc --noEmit`, Vitest and the build pass | `make test-frontend` |
| API from the browser? | A SolidStart catch-all server route proxies `/api/**` to :8050 and streams both ways (SSE-safe); the demo-clock header passes through | `curl :3050/api/v1/auth/session` |

### Data sources

| Source | Result | Decision |
|---|---|---|
| **USITC HTS REST API** | `GET /reststop/exportList?from=&to=&format=JSON` returns clean JSON (htsno, indent, description, units, general/special/other, footnotes) **for the current revision only**. `releaseList` lists every revision with in-force dates: **2026 Revision 3 in force from 12 Feb 2026** (no end date published on the demo day). Archived revisions download only as PDF (`/reststop/file?release=2026HTSRev3&filename=finalCopy` or per chapter). Python's urllib hung on IPv6 to this host while curl worked; the fetcher prefers IPv4 | Fetch the JSON for structure and text; pin the demo to the Revision 3 reading by checking the lines we use against the Revision 3 PDFs (docs/DATA.md) |
| **CBP CROSS rulings** | rulings.cbp.gov's search API refuses scripted requests ("Security parameters are missing from this request context."). There is no bulk export, and we did not try to get around the protection | Use the closest working path: a public Hugging Face mirror of CROSS with ruling number, date, tariff number and the full letter (`orlandowhite/hts-cross-rulings`). Stream-parsed: **18,136 NY/HQ rulings from Jan 2014 to Aug 2025**. Labels are re-derived from each letter's holding (70% of letters state one; 97% of those agree with the mirror's code). The ATLAS dataset (Flexify.AI, 2025) was also checked: it has no ruling numbers or dates, so it can't support citations or date splits |
| **CBSA Customs Tariff 2026** | Published as PDF, a Microsoft Access export (1.1 MB zip) and **HTML per chapter** with a clean table (tariff item, suffix, description, unit, MFN, preferential treatments). T2026 is effective 1 Jan 2026; later consolidations exist, so the demo pins T2026 | Parse the chapter HTML (no Access driver needed) |
| **Duty layers** | Every layer verified against primary sources as of 19 Feb 2026 (Federal Register, executive orders, the Revision 3 Chapter 99, USTR, Canada Gazette, CBSA notices): 33 layers with Chapter 99 numbers, effective dates, scope, stacking rules and sources | `backend/tariffcompass/duties/data/layers.json` |
| **CBSA memoranda** | D11-11-3 (advance rulings), D10-0-1 (parts and accessories), D10-14-64 (Bluetooth goods), D11-6-6 (corrections, 90 days) and D17-1-21 (records, six years) verified. **D10-14-1 does not exist on CBSA's D10 index** and returns 404 | Never cite D10-14-1 |
| **De minimis** | Suspended for all countries from 29 Aug 2025 (EO 14324) | A dated "not applied" line in every US landed cost |

## Decision

Pin these versions (`backend/pyproject.toml`, frozen in `backend/requirements.lock`; `frontend/package.json` exact
pins with `package-lock.json`, `.nvmrc` 21.7.1):

- **Python:** `Django==5.2.19`, `django-ninja==1.8.0`, `pydantic==2.14.3`, `huey==3.5.4`, `tantivy==0.27.0`,
  `dspy==3.5.0`, `gepa==0.1.4`, `numpy==2.5.4`, `scipy==1.18.1`, `scikit-learn==1.9.1`, `lightgbm==4.7.0`,
  `optuna==5.0.0`, `mlflow-skinny==3.18.0`, `pypdf==7.1.0`, `reportlab==5.1.0`, `argon2-cffi==25.1.0`,
  `structlog==26.1.0`, `prometheus-client==0.26.0`, `uvicorn==0.54.0`; dev `pytest==9.2.0`,
  `pytest-django==4.14.0`, `pytest-cov==7.1.0`, `ruff==0.17.5`, `mypy==1.19.1`, `django-stubs==5.2.9`. Optional
  extras: `ai` (`litellm==1.109.1`, only for providers DSPy doesn't reach natively), `postgres`.
- **Web:** `@solidjs/start@1.5.1`, `@solidjs/router@0.15.4`, `@solidjs/meta@0.29.4`, `solid-js@1.9.19`,
  `vinxi@0.5.11`, `@ark-ui/solid@5.40.0`, `tailwind-variants@4.0.2`, `@tanstack/solid-table@8.21.3`,
  `gsap@3.13.0`, `@solid-primitives/media@2.3.6`, `@fontsource/courier-prime@5.2.8`,
  `@fontsource-variable/instrument-sans@5.2.8`; dev
  `tailwindcss@4.1.18`, `@tailwindcss/vite@4.1.18`, `typescript@5.9.3`, `vitest@3.2.7`, `jsdom@26.1.0`,
  `@solidjs/testing-library@0.8.10`, `@types/node@20.19.43`.

## Consequences

- The backend venv is ~570 MB and `node_modules` ~290 MB; both are git-ignored. `data/` holds ~100 MB of rulings.
- Upgrading to SolidStart 2, Vitest 4 or Vite 7+ needs Node 22+; CI uses `.nvmrc` so a bad upgrade fails there
  first.
- The rulings come from a mirror, not CBP directly; every ruling links back to CROSS for the official text, and
  label noise is handled explicitly (ADR 0006).
- `make smoke` re-runs both smoke scripts; CI runs them on every push.

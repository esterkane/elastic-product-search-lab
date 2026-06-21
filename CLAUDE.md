# elastic-product-search-lab — Claude Code Instructions

A compact Elasticsearch e-commerce product-search relevance lab. It compares
product mappings, deterministic ingestion + `search_profile` enrichment, BM25
search strategies, judgment-list relevance metrics (Precision@5, MRR@10,
nDCG@10), latency benchmarks (p50/p95/p99), and a local search-quality gate.
The measurable core loop is **lexical (BM25) + deterministic enrichment**;
vector/hybrid and reranking exist but are optional extras, not the main path.

## Run / test commands

All commands are run from the repo root unless noted. Python is invoked through
the local venv on Windows (`.\.venv\Scripts\python.exe`); on other platforms use
your venv's `python`.

### Quality gate (what CI runs — no Docker/Elasticsearch needed)
```powershell
# Python unit tests (CI excludes integration tests)
.\.venv\Scripts\python.exe -m pytest tests/python -m "not integration"

# API tests, build, lint
cd apps/api
npm ci          # or: npm install
npm test        # vitest run
npm run build   # tsc -p tsconfig.json
npm run lint    # eslint .
```

### Install
```powershell
.\.venv\Scripts\python.exe -m pip install -e .          # core
.\.venv\Scripts\python.exe -m pip install -e ".[esci]"  # optional ESCI dataset prep (pandas, pyarrow)
.\.venv\Scripts\python.exe -m pip install -e ".[vector]" # optional vector/rerank (sentence-transformers, scikit-learn, rank-bm25)
.\.venv\Scripts\python.exe -m pip install -e ".[eval]"   # optional shared relevance-eval skill (git dependency)
cd apps/api && npm install
```

### Local end-to-end (requires Elasticsearch running)
```powershell
docker compose up -d                                          # Elasticsearch + Kibana (security enabled)
.\.venv\Scripts\python.exe scripts\create_index.py --recreate
.\.venv\Scripts\python.exe scripts\load_sample_data.py
cd apps/api && npm run dev                                     # Fastify API on :3000

# Relevance + latency + gate (root):
npm run evaluate:relevance
npm run benchmark:search
npm run gate:search-quality
# ESCI variants: npm run evaluate:relevance:esci / benchmark:search:esci / gate:search-quality:esci

# Relevance via the shared relevance-eval skill (additive; needs the [eval] extra + live ES):
.\.venv\Scripts\python.exe scripts\eval_with_skill.py
```

### Evaluation via the shared `relevance-eval` skill
The Precision@k / MRR@k / nDCG@k math can come from the reusable, backend-agnostic
[`relevance_eval`](https://github.com/esterkane/elastic-ai-search-decision-lab/tree/main/skills/relevance-eval)
skill (installed via the `eval` optional dependency, a git URL) **instead of** this
repo's bespoke metric code. This is **additive** — the original
`scripts/evaluate_relevance.py` + `gate_search_quality.py` + `config/relevance-gate.json`
flow stays intact and is still what `npm run evaluate:relevance` / `gate:search-quality` use.
- `src/eval/skill_adapter.py` — thin adapter: `make_search_fn(client) -> (query, strategy) -> [product_id]`, calling the shared `search_products`. No business logic, no metric math.
- `scripts/eval_with_skill.py` — runner: loads `data/judgments/product_search_judgments.json` + `config/eval_thresholds.json` (the skill's `"<metric>@<k>"` form), calls `relevance_eval.run_evaluation` over the three strategies, writes `reports/relevance.{json,md}`, and exits non-zero when `evaluate_thresholds(...)` fails. Needs a live cluster (integration; run locally).
- `tests/python/test_eval_skill_integration.py` — offline unit tests (fake search, monkeypatched `search_products`); run under `pytest -m "not integration"` once `.[eval]` is installed.

There is **no Python lint or type-check** configured (no ruff/mypy/flake8). Do
not invent one. TypeScript is type-checked via `npm run build` (tsc) and linted
via `npm run lint` (eslint).

### MCP server (read-only agent tools)
```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"   # one-time: install the mcp extra
npm run mcp                                              # stdio server
# equivalently: .\.venv\Scripts\python.exe -m src.mcp.server
```
Exposes `product_search` and `list_strategies` (see `docs/mcp.md`). Unit-tested
in `tests/python/test_mcp_tools.py` with a fake ES client — no live Elasticsearch
needed for the tests; the running server needs ES for `product_search`.

## Architecture in 5 lines
1. **Ingestion** (`src/ingestion/`): deterministic — product ID is the ES doc ID; builds a plain-text `search_profile` field from product attributes before indexing.
2. **Index**: Elasticsearch `products-v1` (mapping in `src/search/product_mapping.json`, `scripts/create_index.py`).
3. **Search API** (`apps/api/`, TypeScript + Fastify): `/search`, `/product`, `/health`, `/metrics`; query DSL built in `src/search/queryBuilder.ts` (baseline BM25, boosted function_score, enriched_profile strategies).
4. **Evaluation** (`src/evaluation/`, `scripts/evaluate_*.py`): judgment lists in `data/` → Precision@5 / MRR@10 / nDCG@10 + latency benchmarks → JSON+MD reports in `reports/`.
5. **Quality gate** (`scripts/gate_search_quality.py`): reads latest relevance+latency reports, fails if thresholds in `config/*.json` are not met.

## Invariants I must never break
1. **Determinism of ingestion/pipeline** — product ID is the ES doc ID; `search_profile` is deterministic plain text derived from product fields. Ingestion and enrichment must stay reproducible; do not introduce nondeterminism.
2. **Passing the quality gate** — `pytest tests/python -m "not integration"`, `npm test`, `npm run build`, `npm run lint` must all pass (this is exactly what CI enforces). Relevance/latency gates (`gate:search-quality`) must not regress below thresholds in `config/relevance-gate.json` / `config/esci-relevance-gate.json`.
3. **Provenance on results** — relevance/latency reports must remain reproducible from judgment lists in `data/` and committed as paired `.json` + `.md` in `reports/`. Gate decisions trace to these reports. (No RAG/LLM citations exist here — this is the nearest real "provenance" concept.)
4. **No secrets in git** — credentials live only in the git-ignored local `.env`. `.env.example` documents variables with placeholders only. Compose reads `ELASTICSEARCH_PASSWORD` / `KIBANA_SYSTEM_PASSWORD` from the environment (`${VAR:?...}`); never hardcode real passwords.

Repo-specific invariants:
- **CI stays Docker-free.** CI must not require Docker or a live Elasticsearch. Full relevance/latency evaluation is local-only; keep integration tests behind the `integration` pytest marker (`-m "not integration"`).
- **Strategies are comparable.** The baseline_bm25 / boosted_bm25 / enriched_profile strategies must remain side-by-side comparable so the relevance-vs-latency trade-off stays measurable.
- **"Hybrid retrieval only" does NOT apply.** The main loop is intentionally lexical BM25 + enrichment. Vector/hybrid/rerank code (`src/search/hybrid_search.py`, `src/search/rerank.py`) is optional and not part of the default gate. Do not force the main search path to be vector/hybrid.
- **Every new Python module under `src/` should get a test** in `tests/python/`.
- **The MCP server stays thin and read-only.** `src/mcp/` contains no business
  logic: tools validate inputs and delegate to `src/search/strategies.py` (the
  single source of truth shared with the eval/benchmark CLIs). No writes, no
  ingestion. Tools return the API's shaped product objects, never raw ES hits,
  and every failure maps to the structured `{ isError, errorCategory:
  validation|transient|business, isRetryable, message, details }` contract — no
  stack traces. Keeping the strategy registry shared means the three strategies
  stay comparable and the search-quality gate is unaffected. Lexical + enrichment
  is intentional; vector/hybrid is optional and not exposed via MCP.

## Definition of done
- [ ] `pytest tests/python -m "not integration"` passes.
- [ ] `npm test` (vitest) passes; `npm run build` (tsc type-check) passes; `npm run lint` (eslint) passes.
- [ ] Search-quality gate not regressed (if relevance/latency were touched and ES is available locally).
- [ ] Reports regenerated and committed as paired `.json` + `.md` in `reports/` when evaluation logic changes.
- [ ] README / `docs/` updated when behavior or commands change.
- [ ] No secrets added; `.env` stays ignored, `.env.example` placeholders only.
- [ ] If MCP tools changed: `src/mcp/` stays thin + read-only, returns API-shaped
      objects with the structured error contract, and `tests/python/test_mcp_tools.py`
      passes. `docs/mcp.md` updated.

## Services & config
- **Elasticsearch 9.3.0** (`:9200`, security enabled, `elastic` superuser) and **Kibana 9.3.0** (`:5601`) via `docker-compose.yml`.
- API config from env (`apps/api/src/config.ts`): `ELASTICSEARCH_URL`, `ELASTICSEARCH_USERNAME/PASSWORD`, `ELASTICSEARCH_USE_AUTH`, `PRODUCT_INDEX` (default `products-v1`), `PORT` (default 3000).
- Python config loads `.env` via `python-dotenv`.
- No external LLM or cloud services required.

# elastic-product-search-lab — Claude Code notes

Compact Elasticsearch product-search relevance lab: product mapping, deterministic
ingestion + `search_profile` enrichment, BM25 search strategies, judgment-list
relevance metrics, latency benchmarks, and local quality gates. A TypeScript
search API lives under `apps/api/`; the measurable Python core lives under `src/`.

## Repo gate (must stay green)
- Python unit tests: `pytest tests/python -m "not integration"`
- API tests + build: `npm test` / `npm run build` in `apps/api`
- Integration tests (`-m integration`) need a live Elasticsearch and are local-only.

## How It Learns

The lab implements the **procedural-learning** half of a memory/learning loop —
an **experiment store plus a tuner**. There is no agent loop, so there is no
episodic recall-before-acting; the experiment store *is* the memory.

- **Experiment store** (`src/learning/experiments.py`): persists each tried
  configuration as `{id, timestamp, config, metrics, gate_passed}` to a committed
  JSON-lines log under `experiments/` — reusing existing infra, **no new
  datastore / no vector DB**. Behind an `ExperimentStore` abstraction with a
  `FileExperimentStore` and an `InMemoryExperimentStore` fake for tests.
- **Tunable config** (`src/learning/config.py`): the per-field boosts of a
  strategy's `multi_match` query (e.g. `search_profile^3`, `title^2`). Baseline
  boosts are copied from the live strategies; the live query builders are never
  mutated by the tuner.
- **Tuner** (`src/learning/tuner.py`): deterministically proposes the next config
  (coordinate ascent over one boost at a time — no randomness), evaluates it over
  the checked-in judgments **reusing `src/evaluation` for the metric math**, then
  runs the **existing gate** (`scripts/gate_search_quality.py:evaluate_gate`). It
  keeps a proposal **only if the gate passes AND the headline metric (Precision@5)
  improves vs the current best**; otherwise it is rejected. Rejected experiments
  are still recorded.
- **Staging, not promotion**: a kept proposal is *staged* in the store. Promoting
  it to the live default strategy config is a separate, explicit step — the tuner
  never silently changes the live config.
- **`MEMORY_ENABLED`** (default **off**): when off the tuner is inert and the
  existing eval/gate behaviour is reproducible/unchanged. Runner: `scripts/tune.py`
  (`--offline` for a no-ES dry run).

## Definition of Done (learning loop)
- A learned change is proposed, evaluated against the **existing** gate/metrics,
  and kept **only if it improves them**; a worse proposal is rejected and the live
  config is never silently mutated.
- `MEMORY_ENABLED` is off by default; with it off the lab is reproducible.
- Metrics reuse `src/evaluation`; strategies and gate are reused; no new vector DB.
- `pytest tests/python -m "not integration"` passes, including the
  worse-config-rejected test in `tests/python/test_learning_tuner.py`.

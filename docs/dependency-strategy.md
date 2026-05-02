# Dependency Strategy

This project should keep the application dependency surface small and explicit. Runtime-critical libraries must be documented, bounded, and tested in CI. Optional components such as the TEI reranker, local LLM service, or alternative lexical scorers must not appear as implicit requirements.

## Current Dependency Inventory

| Component | Status | Dependency source | Version strategy | Notes |
| --- | --- | --- | --- | --- |
| Python runtime | Runtime-critical | `python:3.12-slim`, `requires-python = ">=3.12"` | Keep Python 3.12 for local, Docker, and CI until a deliberate upgrade branch validates all tests. | The project uses Python 3.12 syntax and async libraries. |
| FastAPI | Runtime-critical | `fastapi>=0.115` | Use a compatible lower bound for MVP; before production, pin a tested minor range such as `fastapi>=0.115,<0.116` or move to a lockfile. | API request/response schemas and error handling depend on it. |
| Uvicorn | Runtime-critical | `uvicorn[standard]>=0.32` | Bound by minor version or lock in deployment images. | API container entrypoint. |
| SQLAlchemy | Runtime-critical | `sqlalchemy>=2.0` | Keep `>=2.0,<3.0`; async API compatibility matters more than newest features. | PostgreSQL full-text retrieval and ingestion storage. |
| asyncpg | Runtime-critical | `asyncpg>=0.30` | Keep a lower bound plus CI coverage; pin in production lockfiles. | PostgreSQL async driver. |
| httpx | Runtime-critical | `httpx>=0.27` | Keep a lower bound for tests; pin or range-bound before production because timeout and exception behavior affects retries. | TEI embedding/reranking and Qdrant HTTP calls. |
| pytest | Development-critical | `pytest>=8.0` | Use `pytest>=8,<9` if pytest 9 behavior changes test discovery or async plugin behavior. | CI and local validation. |
| PostgreSQL + pgvector | Runtime-critical service | `pgvector/pgvector:pg16` | Keep an explicit image tag. For production, pin by digest. | Stores chunk text, metadata, full-text vectors, and optional pgvector backend. |
| Qdrant | Runtime-critical service | `qdrant/qdrant` in Compose | Replace floating image tag with a tested release tag before shared deployments. | Vector search, payload filters, and idempotent upserts depend on API compatibility. |
| TEI embedding | Runtime-critical service for dense retrieval and ingestion | `ghcr.io/huggingface/text-embeddings-inference:cpu-latest` | Replace `cpu-latest` with a tested version or digest before production. Keep model ID explicit. | Model startup and output schema are reliability risks. |
| TEI reranker | Optional runtime service | Same TEI image with `TEI_RERANK_MODEL` | Keep optional behind Compose `rerank` profile. Pin model and image together when enabling by default. | Cross-encoder style reranking is slower and memory-sensitive. |
| Ollama/local LLM | Optional service | `ollama/ollama` in Compose | Keep optional until answer generation depends on it. Pin model and server image when used in tests. | Current answer path is deterministic evidence synthesis, not an LLM chain. |
| React | Runtime-critical frontend | `react` and `react-dom` with caret ranges | Use lockfile-backed installs. If no lockfile is committed, CI can drift. | UI rendering and state management. |
| Vite/TypeScript | Build-critical frontend | `vite`, `typescript`, `@vitejs/plugin-react` | Commit a lockfile or pin exact versions before production. | Build behavior can change across minor releases. |
| lucide-react | UI runtime | `lucide-react` caret range | Lock or pin if icons are part of visual regression expectations. | Icons only; low behavioral risk. |

## Stale Or Ambiguous Dependencies

- `rank-bm25` is not installed. Lexical scoring currently uses PostgreSQL `ts_rank_cd` and `websearch_to_tsquery`, so adding `rank-bm25` would duplicate the lexical path unless there is a deliberate offline-ranking use case. If added later, pin `rank-bm25==0.2.2` or replace it with a maintained alternative only after golden-query comparison.
- Sentence Transformers is not installed in this app. Reranking is currently served through TEI-compatible HTTP, which keeps PyTorch and model weights out of the API image. If local in-process reranking is added, isolate it in an optional dependency group such as `rerank-local = ["sentence-transformers>=5.4,<6"]`.
- Frontend dependencies use caret ranges and there is no committed package lockfile. This is acceptable for rapid MVP work but ambiguous for reproducible CI. Commit `frontend/package-lock.json` and switch Docker/CI installs to `npm ci` once the dependency set stabilizes.
- Docker images for Qdrant, TEI, Ollama, Node, Nginx, and Python use tags rather than digests. Tags are readable for development, but production releases should pin digests or use Dependabot-managed version bumps.

## Version And Upgrade Policy

Use three dependency tiers:

| Tier | Examples | Policy |
| --- | --- | --- |
| Runtime-critical | FastAPI, SQLAlchemy, asyncpg, httpx, PostgreSQL/pgvector, Qdrant, TEI embed, React | Use compatible ranges during MVP, then lock or pin before production. Every upgrade must run backend tests, frontend build, Compose validation, and at least one degraded retrieval test. |
| Optional runtime | TEI rerank, Ollama/local LLM | Keep behind explicit profiles or feature flags. Failure must degrade with warnings instead of blocking unrelated workflows. |
| Development-only | pytest, TypeScript, Vite plugin, type packages | Keep CI current, but avoid unrelated major upgrades in feature PRs. |

Recommended next pins and ranges:

- Backend Python package ranges: keep `sqlalchemy>=2.0,<3.0`, consider `fastapi>=0.115,<0.116`, `uvicorn[standard]>=0.32,<0.33`, `httpx>=0.27,<1.0`, `asyncpg>=0.30,<1.0`, and `pytest>=8,<9`.
- Frontend: commit a lockfile first. After that, Docker and CI should use `npm ci` instead of `npm install`.
- Services: replace `qdrant/qdrant`, `ghcr.io/huggingface/text-embeddings-inference:cpu-latest`, and `ollama/ollama` with tested tags. Use digest pins for release builds.
- Reranker models: pin model IDs and record whether the model returns logits, normalized scores, or another score shape. Score interpretation affects UI explanations and golden-query thresholds.

## Changelog Note

Unreleased dependency-policy note:

- Dependency behavior may change when the project moves from broad MVP ranges to lockfile-backed installs and pinned service image tags. Expect more reproducible builds, but also more deliberate upgrade PRs.
- If `rank-bm25` or local Sentence Transformers `CrossEncoder` packages are added later, they should be introduced as optional extras or profile-specific services with explicit tests and documentation.
- Switching frontend installs from `npm install` to `npm ci` will require committing `frontend/package-lock.json` and may change transitive package versions.

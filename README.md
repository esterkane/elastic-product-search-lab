# Elastic Repo Inventory

Elastic Repo Inventory is a local-first search and recommendation tool for selected Elastic documentation repositories. It clones source repos, inventories their structure, ingests Markdown with canonical provenance, generates embeddings, and serves grounded search, answer, and recommendation APIs through FastAPI and a React UI.

## Quick Start

Prerequisites:

- Docker Desktop with Compose
- Git
- Python 3.12 for local CLI and test runs
- Node.js 22 for frontend development outside Docker

Start the full local stack:

```powershell
docker compose up -d --build
```

Open the app:

- Frontend: http://localhost:5173
- API health: http://localhost:8000/api/v1/health
- Qdrant: http://localhost:6333
- Prometheus: http://localhost:9090

From the UI, click **Sync & index changes** to clone or update the configured source repositories and index new or changed Markdown chunks. The first run indexes available content. Later runs compare deterministic chunk IDs and stored content, then embed only new or changed chunks.

The reranker model is optional in local development because it can reserve several GiB of memory while ingestion only needs the embedding model. Enable it when needed:

```powershell
$env:TEI_RERANK_URL="http://tei-rerank/rerank"
docker compose --profile rerank up -d
```

## Inventory CLI

The repository inventory CLI writes deterministic artifacts for the configured Elastic repos:

```powershell
python tools/repo_inventory.py
```

Outputs:

- `sources/` for cloned repositories
- `artifacts/repo-manifest.json`
- `artifacts/repo-manifest.md`

Useful options:

```powershell
python tools/repo_inventory.py --skip-update
python tools/repo_inventory.py --sources-dir C:\tmp\sources --artifacts-dir C:\tmp\artifacts
```

## Architecture

- `tools/repo_inventory.py`: clones or updates source repositories and emits repo manifests.
- `backend/app/ingest`: parses Markdown frontmatter/headings, computes stable anchors, classifies content, records source metadata, and creates deterministic chunks.
- `backend/app/embeddings`: calls a TEI-compatible embedding endpoint.
- `backend/app/vector`: supports Qdrant and pgvector-style vector repository interfaces.
- `backend/app/retrieval`: combines PostgreSQL full-text search and dense retrieval with reciprocal rank fusion and optional reranking.
- `backend/app/recommend`: produces short grounded recommendations with source links.
- `backend/app/api`: exposes ingestion, search, analyze, answer, health, and metrics endpoints.
- `frontend/src`: React + TypeScript UI for search, evidence, analysis, recommendations, filters, and incremental indexing.

## Source Attribution And Licensing

Every indexed chunk must retain:

- source repository slug
- repository URL
- relative path
- commit SHA
- canonical source URL
- content type
- license family

Answers and recommendations must include direct source links. Do not merge evidence from different repositories without preserving each source URL and license family. New ingestion code should treat provenance metadata as required data, not optional display text.

## Deterministic Evaluation

Chunk IDs are generated from:

```python
sha256(f"{repo}:{path}:{anchor}:{chunk_index}".encode()).hexdigest()
```

Evaluation runs should use pinned queries, deterministic ordering, and stable metric implementations. Current metrics include NDCG@10, MRR@10, and Recall@20.

Run backend tests:

```powershell
python -m pytest -p no:cacheprovider
```

Run frontend build:

```powershell
cd frontend
npm install
npm run build
```

Validate Docker Compose:

```powershell
docker compose config --quiet
```

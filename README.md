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
docker compose up -d --force-recreate api
```

The local reranker profile uses conservative request and batch limits by default. Override `TEI_RERANK_MAX_CONCURRENT_REQUESTS`, `TEI_RERANK_MAX_BATCH_REQUESTS`, or `TEI_RERANK_TOKENIZATION_WORKERS` only if the machine has enough spare CPU and memory.

## Configuration Reference

This project currently uses environment variables from `docker-compose.yml`; there is no checked-in `config.example.yaml` or `Makefile`.

Required runtime dependencies:

- Docker Desktop with Compose, used to run PostgreSQL, Qdrant, TEI, the API, worker, frontend, and Prometheus.
- Git, used by ingestion to clone and update the configured source repositories.
- PostgreSQL with pgvector image `pgvector/pgvector:pg16`, used for metadata, chunk text, and full-text retrieval.
- Qdrant, used for vector search over embedded chunks.
- TEI embedding service, used by ingestion and query-time dense retrieval.

Optional runtime dependencies:

- TEI reranker service, enabled with the Compose `rerank` profile and `TEI_RERANK_URL`.
- Ollama `llm` service, exposed through `LLM_URL`; the current answer path is evidence synthesis, not an LLM generation chain.
- Prometheus, used for local service scraping.
- Python 3.12 and Node.js 22, only needed when running CLI, tests, or frontend development outside Docker.

| Key | Required | Default | Valid values | Used by | Failure symptoms |
| --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | Yes for API and worker | Compose builds `postgresql+asyncpg://repo_inventory:repo_inventory@postgres:5432/repo_inventory` | SQLAlchemy async PostgreSQL URL | Retrieval, ingestion | `/api/v1/search` returns `503 retrieval_not_configured`; API cannot query chunks. |
| `POSTGRES_DB` | Yes for Compose Postgres | `repo_inventory` | Non-empty database name | Postgres, `DATABASE_URL` | Postgres health check fails or API connects to the wrong database. |
| `POSTGRES_USER` | Yes for Compose Postgres | `repo_inventory` | Non-empty user name | Postgres, `DATABASE_URL` | Authentication failures in API logs. |
| `POSTGRES_PASSWORD` | Yes for Compose Postgres | `repo_inventory` | Non-empty password | Postgres, `DATABASE_URL` | Authentication failures in API logs. |
| `POSTGRES_PORT` | Optional | `5432` | TCP port `1-65535` | Host access to Postgres | Local port bind conflict or unreachable database from host tools. |
| `QDRANT_URL` | Yes for API and worker | `http://qdrant:6333` | HTTP URL | Dense retrieval, vector upsert | `/api/v1/search` returns `503 retrieval_not_configured` or vector search/upsert fails. |
| `QDRANT_COLLECTION` | Optional | `repo-docs` | Non-empty collection name | Qdrant vector repository | Empty search results if API points at a different collection than ingestion. |
| `QDRANT_API_KEY` | Optional | unset | API key string | Qdrant client | Unauthorized responses when using secured Qdrant. |
| `QDRANT_HTTP_PORT` | Optional | `6333` | TCP port `1-65535` | Host access to Qdrant REST | Qdrant UI/API is not reachable from the host. |
| `QDRANT_GRPC_PORT` | Optional | `6334` | TCP port `1-65535` | Host access to Qdrant gRPC | Port bind conflict if another service uses it. |
| `TEI_IMAGE` | Optional | `ghcr.io/huggingface/text-embeddings-inference:cpu-latest` | TEI-compatible image | Embedding and reranking services | Container pull/start failures. |
| `TEI_EMBED_URL` | Yes for API and worker | `http://tei-embed/embed` | TEI-compatible `/embed` endpoint | Embedding client | Ingestion fails during embedding; dense retrieval cannot embed the query. |
| `TEI_EMBED_MODEL` | Optional | `BAAI/bge-small-en-v1.5` in Compose service | TEI-supported embedding model ID | TEI embed service/client metadata | Model download/startup failure or embedding dimension mismatch after changing models. |
| `TEI_EMBED_PORT` | Optional | `8081` | TCP port `1-65535` | Host access to TEI embed | Host cannot call the embedding endpoint directly. |
| `INGEST_EMBED_BATCH_SIZE` | Optional | `8` | Positive integer; keep small on CPU-only machines | Ingestion | Large values can increase memory pressure or TEI latency. |
| `INGEST_UPSERT_BATCH_SIZE` | Optional | `64` | Positive integer | Ingestion | Very large values can make upserts slower to retry after failures. |
| `TEI_RERANK_URL` | Optional | unset | TEI-compatible `/rerank` endpoint, for Compose use `http://tei-rerank/rerank` | Retrieval reranker | If unset, reranking is skipped; if wrong, answer/search requests can fail when reranker is enabled. |
| `TEI_RERANK_MODEL` | Optional | `BAAI/bge-reranker-base` in Compose service | TEI-supported reranker model ID | TEI rerank service/client metadata | Rerank container fails to start or returns malformed scores. |
| `TEI_RERANK_PORT` | Optional | `8082` | TCP port `1-65535` | Host access to TEI rerank | Host cannot call reranker directly. |
| `TEI_RERANK_TOKENIZATION_WORKERS` | Optional | `2` | Positive integer | TEI rerank service | Too high can increase CPU and memory contention. |
| `TEI_RERANK_MAX_CONCURRENT_REQUESTS` | Optional | `16` | Positive integer | TEI rerank service | Too high can cause high memory use or container exits. |
| `TEI_RERANK_MAX_BATCH_REQUESTS` | Optional | `4` | Positive integer | TEI rerank service | Too high can increase latency and memory use. |
| `TEI_RERANK_MAX_CLIENT_BATCH_SIZE` | Optional | `8` | Positive integer | TEI rerank service | Large values can overload CPU-only reranking. |
| `TEI_RERANK_MAX_BATCH_TOKENS` | Optional | `2048` | Positive integer token budget | TEI rerank service | Too low truncates useful context; too high can exhaust memory. |
| `LLM_URL` | Optional | `http://llm:11434` | HTTP URL | Future/local LLM backend integration | No current answer-path symptom; future LLM calls would fail if unreachable. |
| `OLLAMA_PORT` | Optional | `11434` | TCP port `1-65535` | Host access to Ollama | Host cannot reach Ollama directly. |
| `API_PORT` | Optional | `8000` | TCP port `1-65535` | Host access to FastAPI | Frontend proxy/API calls fail if mapped differently without matching client config. |
| `FRONTEND_PORT` | Optional | `5173` | TCP port `1-65535` | Host access to React UI | Browser cannot reach the UI at the expected port. |
| `PROMETHEUS_PORT` | Optional | `9090` | TCP port `1-65535` | Host access to Prometheus | Metrics UI is not reachable from the host. |
| `APP_ENV` | Optional | `local` | Environment label string | API and worker | No direct failure symptom today; useful for future environment-specific behavior. |
| `SOURCES_DIR` | Optional | `/app/sources` in Compose, `sources` locally | Writable directory path | Ingestion | Clone/update fails or ingestion cannot find local repositories. |
| `WORKER_READY_FILE` | Optional | `/tmp/worker-ready` | Writable file path | Worker health check | Worker remains unhealthy if the path cannot be written. |
| `WORKER_IDLE_SECONDS` | Optional | `30` | Positive integer seconds | Worker loop | Invalid values crash the worker at startup. |

OCR configuration keys: none are implemented today. If PDF or scanned-document ingestion is added, document the OCR engine URL, language list, DPI/page limits, timeout, and confidence threshold here before wiring it into ingestion.

## First Successful Run

Use this checklist to prove the full local path works before tuning relevance:

1. Start the stack: `docker compose up -d --build`.
2. Check health: open `http://localhost:8000/api/v1/health` and confirm `{"status":"ok"}`.
3. Open the UI at `http://localhost:5173`.
4. Click **Sync & index changes** and wait for the success banner.
5. Confirm Qdrant is reachable at `http://localhost:6333` and Prometheus at `http://localhost:9090`.
6. Search for `When should I use reranking after hybrid retrieval?`.
7. Verify the results list contains direct GitHub source links from the active repositories.
8. Verify the answer panel gives a short grounded answer and shows source attributions.
9. Optional: enable reranking with `$env:TEI_RERANK_URL="http://tei-rerank/rerank"`, then run `docker compose --profile rerank up -d` and `docker compose up -d --force-recreate api`.
10. Repeat the same query and compare result ordering, source diversity, and answer quality.

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

The application is built as a provenance-first retrieval pipeline: source material is normalized into deterministic chunks, each chunk keeps its canonical source metadata, and every answer or recommendation is assembled from ranked evidence rather than free-floating generated text. The current implementation ingests Markdown from the configured Elastic repositories. If PDF support is added later, a PDF adapter should first extract text and page-level provenance, then pass that normalized content into the same document and chunk model instead of bypassing the existing metadata rules.

For the example query `When should I use reranking after hybrid retrieval?`, the flow is:

1. `tools/repo_inventory.py` and `backend/app/ingest/indexer.py` clone or update `elastic/docs-content`, `elastic/elasticsearch-labs`, and `elastic/labs-releases` under `sources/`.
2. `backend/app/ingest/parser.py` parses Markdown frontmatter and headings; `backend/app/ingest/chunker.py` creates stable anchors and deterministic chunk IDs from `repo:path:anchor:chunk_index`.
3. `backend/app/ingest/license.py` records the source license family, while each chunk stores repo, path, commit SHA, canonical source URL, content type, heading path, and license metadata.
4. Chunk text is stored in PostgreSQL for lexical full-text search, and embeddings from `backend/app/embeddings/client.py` are upserted into Qdrant through `backend/app/vector/qdrant_client.py`.
5. `backend/app/retrieval/service.py` runs PostgreSQL full-text search and dense vector search, merges candidates with reciprocal rank fusion, de-duplicates overlapping source pages, and optionally calls the TEI reranker when `TEI_RERANK_URL` is configured.
6. `backend/app/api/search.py` returns evidence-backed search and answer responses with direct source attributions; `backend/app/recommend/service.py` groups improvement suggestions into relevance, ingestion, mapping, performance, and resiliency categories.
7. `frontend/src` presents the ranked results, synthesized answer, source links, filters, and incremental indexing control in the React UI.

```mermaid
flowchart LR
    A["Source repositories / future extracted PDF text"] --> B["Inventory and ingestion"]
    B --> C["Markdown parser and canonical metadata"]
    C --> D["Deterministic chunks with source URLs"]
    D --> E["PostgreSQL full-text index"]
    D --> F["TEI embeddings"]
    F --> G["Qdrant vector store"]
    E --> H["Hybrid retrieval"]
    G --> H
    H --> I["RRF merge and source de-duplication"]
    I --> J["Optional TEI reranker"]
    J --> K["Evidence-backed answer"]
    I --> L["Improvement recommendations"]
    K --> M["React UI"]
    L --> M
```

In practice, the query `When should I use reranking after hybrid retrieval?` should retrieve broad BM25 and semantic candidates first, then use reranking only on the smaller merged candidate set when better ordering is worth the extra latency and memory. The UI should show both the answer and the specific documentation or lab sources that support it.

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

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

For dependency hygiene, version ranges, optional OCR/reranker/Gradio guidance, and upgrade policy, see [Dependency Strategy](docs/dependency-strategy.md).

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
| `RETRIEVAL_RETRY_ATTEMPTS` | Optional | `2` | Positive integer | Retrieval wrappers | Too low exposes transient failures; too high increases request latency during outages. |
| `RETRIEVAL_RETRY_BACKOFF_SECONDS` | Optional | `0.2` | Non-negative seconds | Retrieval wrappers | Too low can hammer unhealthy services; too high slows degraded responses. |
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

## When To Rerank After Hybrid Retrieval

Current excerpt from this README:

> In practice, the query `When should I use reranking after hybrid retrieval?` should retrieve broad BM25 and semantic candidates first, then use reranking only on the smaller merged candidate set when better ordering is worth the extra latency and memory.

Current behavior in `backend/app/retrieval/service.py`:

> The service retrieves up to 50 lexical hits and 50 dense hits, merges them with reciprocal rank fusion, keeps the top 20 fused candidates, and reranks those 20 only when `TEI_RERANK_URL` is configured.

Use reranking when you have a small merged candidate set and relevance quality matters more than raw latency. Do not run the reranker over the whole corpus. The first stage should be cheap and broad: BM25 catches exact terms, dense retrieval catches semantic matches, and reciprocal rank fusion creates a balanced candidate pool without requiring score calibration between lexical and vector systems. The reranker is the second stage: it spends more compute on the top candidates by comparing the user query directly with candidate text.

For the query `When should I use reranking after hybrid retrieval?`, the decision rule is:

1. Run first-stage retrieval with both lexical and dense search.
2. Merge candidates with RRF so documents that rank well in either channel can survive.
3. Keep a bounded rerank window. This repo uses 20 fused candidates today; Elastic examples commonly show explicit rerank windows such as `rank_window_size` to control the cost of the second stage.
4. Rerank only when the query is ambiguous, answer quality matters, or the top results will feed an evidence-backed answer or recommendation.
5. Skip reranking when latency, CPU, or memory is the bottleneck, or when hybrid results are already stable and easy to explain.

| Mode | What happens | Best for | Cost and latency | Score explanation |
| --- | --- | --- | --- | --- |
| Hybrid only | PostgreSQL full-text search and Qdrant dense search run first-stage retrieval, then RRF merges lexical and semantic rankings. | Fast exploration, broad recall, local development, and queries where exact matches are already strong. | Lower latency. No reranker container required. | Explain that ranking comes from fused lexical and dense rank positions; raw BM25 and vector scores are not directly comparable. |
| Hybrid plus rerank | Hybrid retrieval creates the candidate set, then the reranker reorders the top fused candidates by query-document semantic fit. | Ambiguous natural-language questions, answer generation, RAG-style evidence selection, and cases where top results look plausible but not best ordered. | Higher latency and memory use. Keep the rerank window small and monitor `tei-rerank` CPU and memory. | Explain that final order may change because the reranker reads the query and candidate text together; show source links and, when exposed, lexical, dense, fused, and rerank scores. |

Candidate limits are the main control knob. Larger first-stage pools can improve recall, but they also create more work before fusion. Larger rerank windows can improve ordering, but cost grows with each query-candidate pair sent to the reranker. For this app, start with the current behavior: retrieve 50 lexical plus 50 dense candidates, fuse to 20, then return the requested limit after source de-duplication. Increase the rerank window only after measuring answer quality and latency on pinned queries.

Skip reranking when:

- The query is navigational, such as an exact title, path, repo, or API name.
- The UI needs the fastest possible results and answer synthesis is not required.
- The reranker service is unhealthy, memory-constrained, or adding timeouts.
- The result set is already dominated by one clearly correct source.
- You cannot explain the changed ordering to the user with source links and score metadata.

Score transparency matters because reranking can move a result that was not first in BM25 or vector search to the top. The backend already tracks `lexical_score`, `dense_score`, and `rerank_score` on `RankedHit`, while the API response currently exposes only the final `score`. If users need to understand why rankings changed, extend the response model to include the component scores, the retrieval channels that found each hit, and whether the final score came from RRF or reranking.

Use query explain mode when validating ranking changes. Set `explain: true` on `POST /api/v1/search` or enable **Explain scores** in the UI. Result cards then show `bm25`, `semantic`, `fusion`, `rerank`, and `final rank` for each returned hit. When reranking is disabled, `rerank` is shown as skipped and the final score remains the fusion score. This directly answers the reranking decision question: rerank after hybrid retrieval when the first-stage candidate pool is already good and you need better final precision, especially for user-facing evidence or RAG contexts.

Example debug response shape:

```json
{
  "score_breakdown": {
    "bm25": 0.42,
    "semantic": 0.61,
    "fusion": 0.53,
    "rerank": 0.88,
    "final_rank": 1,
    "final_score": 0.88
  }
}
```

## Chunk Metadata And Evidence Schema

Current excerpt from this README:

> Every indexed chunk must retain: source repository slug, repository URL, relative path, commit SHA, canonical source URL, content type, license family.

Current behavior in `frontend/src/components/ResultCard.tsx`:

> Result cards choose `title`, `heading_path`, `path`, or `id` as the visible title, then show the score, content type, license family, and direct source link.

The ingestion pipeline treats metadata as part of the evidence contract, not decoration. Every chunk must be traceable back to a repository, path, heading anchor, commit, license family, and canonical source URL. That contract is what lets the answer panel explain a query such as `When should I use reranking after hybrid retrieval?` with grounded links instead of only returning plausible text.

### Indexed Chunk Schema

Required stored fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | Yes | Deterministic chunk ID generated from `sha256(repo:path:anchor:chunk_index)`. |
| `content` | Yes | Markdown section text that is embedded, searched, and shown as evidence context. |
| `repo` | Yes | Repository slug, such as `elastic/docs-content`. |
| `path` | Yes | Repository-relative source path. |
| `source_url` | Yes | Canonical GitHub URL pinned to the indexed commit and heading anchor when available. |
| `commit_sha` | Yes | Source commit used for the indexed content. |
| `content_hash` | Yes | Hash used to detect changed chunks during incremental ingestion. |
| `metadata` | Yes | JSON payload shared with vector search and API responses. |
| `search_vector` | Yes | PostgreSQL full-text search vector derived from `content`. |
| `updated_at` | Yes | Database timestamp for the stored chunk row. |

Required metadata keys:

| Metadata key | Required | Meaning |
| --- | --- | --- |
| `repo` | Yes | Normalized repository filter and evidence provenance field. |
| `path` | Yes | Normalized path filter and source attribution field. |
| `source_url` | Yes | Direct evidence link for answers, recommendations, and result cards. |
| `commit_sha` | Yes | Commit provenance for reproducible evidence. |
| `content_type` | Yes | Classified type, for example `documentation`, `notebook`, or `release`. |
| `license_family` | Yes | License family inferred from the source repository. |
| `anchor` | Yes | Stable heading anchor, or `document` for unheaded content. |
| `chunk_index` | Yes | Zero-based chunk number within the heading section. |

Optional metadata keys:

| Metadata key | Required | Meaning |
| --- | --- | --- |
| `title` | No | Document title from frontmatter or the first heading. |
| `heading_path` | No | Display heading path used by result cards and answer evidence. |
| `default_branch` | No | Repository default branch, useful for diagnostics and inventory output. |
| `frontmatter_json` | No | Parsed frontmatter stored at the document level. |

Example indexed chunk:

```json
{
  "id": "4f7b0a9d0e7e2f2a8e6c6d4b1a0c2f8d6a7b3c1e9f0a4d5c6b7a8e9f1d2c3b4a",
  "content": "Semantic reranking improves the order of a smaller candidate set after first-stage retrieval.",
  "repo": "elastic/docs-content",
  "path": "solutions/search/ranking/semantic-reranking.md",
  "source_url": "https://github.com/elastic/docs-content/blob/<commit_sha>/solutions/search/ranking/semantic-reranking.md#use-cases-semantic-reranking-use-cases",
  "commit_sha": "<commit_sha>",
  "content_hash": "sha256:<content_hash>",
  "metadata": {
    "repo": "elastic/docs-content",
    "path": "solutions/search/ranking/semantic-reranking.md",
    "title": "Semantic reranking [semantic-reranking]",
    "heading_path": "Semantic reranking [semantic-reranking] > Use cases [semantic-reranking-use-cases]",
    "content_type": "documentation",
    "license_family": "elastic-license",
    "source_url": "https://github.com/elastic/docs-content/blob/<commit_sha>/solutions/search/ranking/semantic-reranking.md#use-cases-semantic-reranking-use-cases",
    "commit_sha": "<commit_sha>",
    "anchor": "use-cases-semantic-reranking-use-cases",
    "chunk_index": 0
  }
}
```

### UI Evidence Card Schema

The API response for `POST /api/v1/search` becomes the result-card and answer evidence schema. The UI must preserve source attribution even when a title or heading is missing.

Required displayed-result fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | Yes | Chunk ID returned by lexical or vector retrieval. |
| `score` | Yes | Final score after fusion or reranking. |
| `source_url` | Yes | Direct link used by the `Open source` action and answer citations. |

Optional displayed-result fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `title` | No | Preferred visible title. |
| `repo` | No | Repository badge and filter context. |
| `path` | No | Repository-relative source path shown under the title. |
| `heading_path` | No | Heading breadcrumb shown under the title. |
| `content_type` | No | Content type badge. |
| `license_family` | No | License badge used for provenance review. |
| `score_breakdown` | No | Explain-mode details for `bm25`, `semantic`, `fusion`, `rerank`, `final_rank`, and `final_score`. |

Example displayed result:

```json
{
  "id": "4f7b0a9d0e7e2f2a8e6c6d4b1a0c2f8d6a7b3c1e9f0a4d5c6b7a8e9f1d2c3b4a",
  "score": 0.88,
  "title": "Semantic reranking [semantic-reranking]",
  "repo": "elastic/docs-content",
  "path": "solutions/search/ranking/semantic-reranking.md",
  "heading_path": "Semantic reranking [semantic-reranking] > Use cases [semantic-reranking-use-cases]",
  "content_type": "documentation",
  "license_family": "elastic-license",
  "source_url": "https://github.com/elastic/docs-content/blob/<commit_sha>/solutions/search/ranking/semantic-reranking.md#use-cases-semantic-reranking-use-cases",
  "score_breakdown": {
    "bm25": 0.42,
    "semantic": 0.61,
    "fusion": 0.53,
    "rerank": 0.88,
    "final_rank": 1,
    "final_score": 0.88
  }
}
```

Evidence provenance rules:

- Answers must cite `source_url` values from returned hits, not generated URLs.
- Result cards must keep `repo`, `path`, `heading_path`, `content_type`, and `license_family` visible when those fields are available.
- Incremental indexing must compare `content_hash` and `commit_sha` before reusing an existing chunk.
- De-duplication should prefer one displayed card per canonical source URL and heading, while preserving distinct chunks when they support different answer evidence.
- The current UI does not expose `commit_sha` as a separate field. The canonical `source_url` is commit-pinned, but expose `commit_sha` in `SearchHitResponse` if reviewers need an explicit audit column.

### Query-Time Filters And Boosts

Metadata is normalized before indexing and again when older rows are read back from storage. The backend treats `repo`, `path`, `heading_path`, `content_type`, and `license_family` as the filterable and boostable evidence fields. Normalization lowercases repository, content-type, and license values, converts Windows path separators to `/`, trims empty values, and fills older rows with `unknown` for missing `content_type` or `license_family`.

Example search request with exact metadata filters and a documentation boost:

```json
{
  "query": "When should I use reranking after hybrid retrieval?",
  "filters": {
    "repo": "elastic/docs-content",
    "content_type": "documentation",
    "license_family": "elastic-license"
  },
  "boosts": {
    "content_type": {
      "documentation": 0.15
    }
  },
  "explain": true
}
```

Filters are strict. Use them when the user intentionally limits the evidence pool, such as one repository, one exact path, or one license family. Boosts are soft. Use them when matching evidence should remain eligible but normalized metadata should influence final ordering. Boosting currently applies after reciprocal rank fusion and before optional reranking, so the reranker can still reorder the boosted candidate pool based on query-document fit.

Backward compatibility and migration:

- Existing `document_chunks` rows can still be queried because `repo` and `path` fall back to their top-level database columns when JSON metadata is missing those keys.
- Existing vector points should continue to return results, but Qdrant filters only match fields present in the payload. Re-run **Sync & index changes** after this patch to refresh vector payloads with normalized `repo`, `path`, `heading_path`, `content_type`, and `license_family`.
- A full rebuild is only needed if old vector payloads were created before metadata normalization and filtered Qdrant searches appear incomplete.

## Operational Reliability Guide

Current excerpt from this README:

> The local reranker profile uses conservative request and batch limits by default. Override `TEI_RERANK_MAX_CONCURRENT_REQUESTS`, `TEI_RERANK_MAX_BATCH_REQUESTS`, or `TEI_RERANK_TOKENIZATION_WORKERS` only if the machine has enough spare CPU and memory.

Current improvement suggestion emitted by the app:

> Add retries and partial-result handling so recommendations still return evidence when one retrieval backend is unavailable.

The reliability contract should keep the application useful whenever at least one grounded retrieval path is healthy. Users should see evidence, source links, and a clear degraded-mode warning instead of a blank answer when Qdrant, TEI reranking, OCR, or one ingestion source has a temporary failure.

### Cache Policy

| Cache | Current behavior | Recommended policy |
| --- | --- | --- |
| TEI model cache | Compose mounts `tei_embed_cache` and `tei_rerank_cache` volumes under `/data`, so model files survive container restarts. | Keep these named volumes. Do not delete them during normal troubleshooting because re-downloading models increases startup time and failure risk. |
| Embeddings | Ingestion stores vectors in Qdrant and avoids re-embedding unchanged chunks by comparing deterministic chunk IDs and content hashes. | Continue using content hashes as the cache key. For query embeddings, add a small TTL cache keyed by normalized query plus model ID if repeated UI queries become expensive. |
| Reranker inputs | No application-level reranker cache is implemented today. | Cache reranker scores by `query`, `chunk_id`, `content_hash`, and reranker model ID. Invalidate when content hash or model changes. |
| OCR output | OCR is not implemented today. | If PDF or scanned-document OCR is added, cache extracted page text by file hash, page number, OCR engine, language list, and DPI. Store OCR confidence and page provenance beside the extracted text. |

### Timeouts And Retries

| Operation | Current timeout source | Retry guidance |
| --- | --- | --- |
| Git sync | `run_git` uses a 300 second subprocess timeout; metadata git reads use 60 seconds. | Retry transient network failures once with backoff. Do not retry permanent checkout or unknown-repository errors. |
| Embedding requests | `EmbeddingClient` uses a 30 second HTTP timeout. | Retry idempotent batch embedding requests on timeout, 429, and 5xx. Keep `INGEST_EMBED_BATCH_SIZE` small on CPU-only machines. |
| Qdrant search/upsert | `QdrantVectorRepository` uses a 30 second HTTP timeout. | Retry vector upserts because point IDs are deterministic and idempotent. For search, retry once, then continue with lexical-only results if PostgreSQL succeeded. |
| PostgreSQL lexical search | SQLAlchemy connection and statement behavior comes from `DATABASE_URL` and the async engine. | Treat PostgreSQL failure as severe because lexical search, chunk text, and metadata live there. If Qdrant still works, return vector-only evidence with a warning. |
| Reranking | `RerankerClient` uses a 30 second HTTP timeout and only runs when `TEI_RERANK_URL` is configured. | Retry once for timeout or 5xx. If reranking still fails, keep fused hybrid results, set rerank to skipped in explain mode, and show a warning badge. |
| OCR | Not implemented. | If OCR is unavailable, skip scanned/PDF-only files, record ingestion warnings, and keep Markdown ingestion running. |

### Fallback Order

Search should degrade in this order:

1. Run PostgreSQL lexical retrieval and Qdrant dense retrieval in parallel where possible.
2. If both retrieval stages succeed, merge with RRF, apply metadata boosts, then optionally rerank.
3. If dense retrieval fails but lexical succeeds, return lexical-only results with direct source links and a warning such as `Semantic retrieval unavailable; showing lexical results.`
4. If lexical retrieval fails but dense retrieval succeeds, return vector-only results with source links and a warning such as `Lexical retrieval unavailable; showing semantic results.`
5. If reranking fails, return fused results and show `Reranker unavailable; ranking uses hybrid fusion.`
6. If OCR is unavailable during ingestion, index Markdown and text sources, mark OCR-backed files as skipped, and show the skipped count in the ingestion response.
7. If no retrieval backend succeeds, return the structured error response instead of fabricating an answer.

The implementation supports a safe configured-off reranker path: when `TEI_RERANK_URL` is unset, results use RRF and explain mode shows `rerank` as skipped. Search, analyze, and answer responses also return `warnings` and `degraded` fields when a retrieval stage fails after retries. The UI displays those warnings above the results instead of hiding missing evidence.

### Partial-Result Semantics

| Failure | User-visible behavior | Answer behavior | Recommendation behavior |
| --- | --- | --- | --- |
| Lexical works, semantic fails | Show lexical results, direct source links, and a warning badge. Score breakdown should show BM25 values and zero or null semantic values. | Generate answers only from lexical evidence and say the result is lexical-only. | Still emit recommendations, but include a resiliency recommendation to restore dense retrieval. |
| Semantic works, lexical fails | Show semantic results and a warning badge. Score breakdown should show semantic values and zero or null BM25 values. | Generate answers only from semantic evidence and say exact-term matching is unavailable. | Recommend checking PostgreSQL health and full-text indexes. |
| Reranker fails | Show fused hybrid results; explain mode displays `rerank: skipped`. | Use top fused evidence. Do not fail answer generation only because reranking failed. | Recommend lowering rerank concurrency or disabling the reranker profile on constrained machines. |
| OCR unavailable | Keep indexing Markdown and already-extracted text. Show skipped OCR document count in ingestion status. | Do not cite unavailable scanned content. | Recommend enabling OCR only after documenting engine URL, language list, DPI/page limits, timeout, and confidence threshold. |

Example degraded but still useful response:

```json
{
  "hits": [
    {
      "id": "4f7b0a9d0e7e2f2a8e6c6d4b1a0c2f8d6a7b3c1e9f0a4d5c6b7a8e9f1d2c3b4a",
      "score": 0.53,
      "title": "Semantic reranking [semantic-reranking]",
      "repo": "elastic/docs-content",
      "path": "solutions/search/ranking/semantic-reranking.md",
      "content_type": "documentation",
      "license_family": "elastic-license",
      "source_url": "https://github.com/elastic/docs-content/blob/<commit_sha>/solutions/search/ranking/semantic-reranking.md#semantic-reranking",
      "score_breakdown": {
        "bm25": 0.42,
        "semantic": 0.61,
        "fusion": 0.53,
        "rerank": null,
        "final_rank": 1,
        "final_score": 0.53
      }
    }
  ],
  "warnings": [
    {
      "code": "reranker_unavailable",
      "message": "Reranker unavailable; ranking uses hybrid fusion."
    }
  ],
  "degraded": true
}
```

Operational checks:

- Use `/api/v1/health` for API liveness and `/api/v1/metrics` for the current endpoint/category surface.
- Use `docker compose ps` and `docker stats --no-stream` when TEI containers exit or memory pressure is suspected.
- Use `docker compose logs --tail=120 api`, `qdrant`, `tei-embed`, or `tei-rerank` to identify the failing stage.
- Monitor top-k latency separately for lexical retrieval, query embedding, vector retrieval, RRF, reranking, and answer synthesis before increasing candidate or rerank windows.

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

See [Validation Strategy](docs/validation-strategy.md) for the public test plan covering ingestion, OCR readiness, hybrid retrieval, reranking, claim-checking, evidence rendering, latency checks, and golden-query evaluation.

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

# Validation Strategy

Elastic Repo Inventory is currently a release-intelligence app for indexed Elastic documentation, not a general-purpose advice generator. Validation should prove that ingestion is deterministic, retrieval remains grounded, and the UI explains Elasticsearch 8.x and 9.x changes with clean source links.

## Coverage Map

| Area | Happy-path coverage | Fallback coverage | Current tests |
| --- | --- | --- | --- |
| Repository inventory | Discovers top-level directories, project files, README-style files, workflow paths, and license files with deterministic ordering. | Handles missing project files and fallback license names. | `tests/test_repo_inventory.py` |
| Markdown ingestion | Parses frontmatter, headings, stable anchors, canonical metadata, content type, license family, content hashes, and deterministic chunk IDs. | Normalizes missing or partial metadata for older indexed rows. | `backend/tests/test_ingest_pipeline.py` |
| Source sync | Updates managed checkouts and recovers from local generated-file churn before indexing. | Reports per-repo sync errors without hiding successful repos. | Backend ingestion tests and local Compose smoke checks |
| Embeddings and vector upsert | Batches TEI-compatible embedding calls and idempotently upserts deterministic vector points. | Accepts TEI response variants and validates deterministic Qdrant/pgvector filters. | `backend/tests/test_vector_upsert.py` |
| Hybrid retrieval | Runs lexical and dense retrieval, merges with reciprocal rank fusion, applies metadata boosts, de-duplicates sources, and preserves score breakdown fields for explain mode. | Returns lexical-only, semantic-only, or fused-without-rerank results with structured warnings. | Backend retrieval/API tests |
| Reranking | Reranks a bounded fused candidate set when the optional reranker is configured. | Retries reranker failures, falls back to fusion, and exposes `reranker_unavailable`. | Backend retrieval/API tests |
| Release-intelligence synthesis | Converts ranked evidence into answer, summary, what is new, what to look for, why it matters, read-first source, related sources, and evidence excerpts. | Avoids overclaiming when evidence is weak and keeps source links attached. | Frontend formatter tests |
| API serialization | Returns typed search, answer, health, metrics, and ingest responses. | Uses structured validation and service-not-configured errors; exposes `warnings` and `degraded`. | `backend/tests/test_api.py` |
| UI rendering | Shows answer-first layout, topic/version/time controls, compact source metadata, highlighted evidence, and warning banners. | Keeps the answer usable when warnings are present and hides advanced/debug details by default. | Frontend tests and Vite build |

## Required Local Checks

Run backend tests before merging ingestion, retrieval, API, or sync changes:

```powershell
python -m pytest -p no:cacheprovider
```

Run frontend tests and the production build before merging UI changes:

```powershell
cd frontend
npm install
npm test -- --run
npm run build
```

Validate local orchestration before merging Docker or dependency changes:

```powershell
docker compose config --quiet
docker compose build api frontend
```

For retrieval or synthesis behavior, add focused tests whenever a change affects ranking, filtering, source attribution, warning semantics, topic classification, version extraction, or answer wording. A good test should pin the query, candidate IDs, metadata, score inputs, final order, warnings, and source URLs.

## Golden Queries

Golden-query tests should be deterministic and small. They should avoid live network dependencies, use mocked lexical/vector/reranker responses, and assert both ranking quality and answer quality.

Release-intelligence smoke queries:

1. `What changed in Elasticsearch 9.x vector search?`
2. `What is new for ES|QL joins in 9.x?`
3. `Which 8.x changes affect ingestion reliability?`
4. `What changed around failure stores and ingest pipelines?`
5. `What relevance and reranking improvements matter for search applications?`
6. `Which mapping or field changes should I review before upgrading?`
7. `What performance improvements affect filtered retrieval latency?`
8. `What breaking changes in 9.x should a search platform team inspect?`

Evidence-quality regression queries:

1. `How should I combine BM25 and semantic search for better relevance?`
2. `When should I use reranking after hybrid retrieval?`
3. `What is the best way to index documentation chunks with stable source links?`
4. `How can I reduce duplicate or overlapping search results?`

Start with these query families:

| Query | Expected behavior | Metrics |
| --- | --- | --- |
| `What changed in Elasticsearch 9.x vector search?` | Prefers 9.x release/docs evidence, explains the engineering impact, and avoids making serverless the primary answer unless requested. | NDCG@10, MRR@10, Recall@20, source-link coverage |
| `Which 8.x changes affect ingestion reliability?` | Surfaces ingestion or failure-handling evidence and explains the practical recovery path. | Topic precision, source-link coverage, summary faithfulness |
| `What is new for ES|QL joins in 9.x?` | Applies version-aware wording and points to the best release-note or docs section. | Version precision, answer usefulness |
| `How do I filter results by repository and license?` | Applies normalized `repo`, `path`, `content_type`, and `license_family` filters deterministically. | Filter precision, zero unexpected repos, stable ordering |
| `What happens if the reranker is unavailable?` | Returns fused results with `reranker_unavailable`, `degraded: true`, and no fabricated evidence. | Warning coverage, Recall@20 against fused baseline |
| `How do I index only new documentation changes?` | Explains incremental indexing with deterministic chunk IDs and content hashes. | Source attribution coverage, answer faithfulness |

Latency checks should record stage timings for lexical retrieval, query embedding, vector retrieval, RRF, reranking, answer synthesis, and UI response time. For local CPU-only development, reranking should be measured separately because model loading and cross-encoder inference dominate perceived latency.

## CI Matrix Proposal

Current CI runs backend tests, frontend build, Docker Compose validation, and an on-demand deterministic evaluation workflow. The next CI matrix should make dependency risk explicit:

| Job | Runtime | Services | Purpose |
| --- | --- | --- | --- |
| `backend-unit` | Python 3.12 | None | Fast parser, chunking, metadata, API, retrieval, fallback, and metric tests. |
| `frontend-test-build` | Node 22 | None | Vitest, TypeScript, and Vite build for answer-first rendering and release controls. |
| `compose-smoke` | Docker | PostgreSQL, Qdrant, API | Health, metrics, structured error responses, and startup dependency checks. |
| `retrieval-degraded` | Python 3.12 | Mocked TEI/Qdrant/Postgres failures | Verifies lexical-only, semantic-only, reranker-failed, and no-evidence semantics. |
| `eval-smoke` | Python 3.12 | Mocked retrieval fixtures | Runs golden queries and records NDCG@10, MRR@10, Recall@20, warning coverage, version precision, topic precision, and source-link coverage. |

Every relevance-affecting pull request should describe the golden queries it changes, the expected ranking movement, and why source attribution remains correct. Dependency upgrades should include at least one fallback test for the upgraded component because vector stores, rerankers, and local model services tend to fail in different ways across versions.

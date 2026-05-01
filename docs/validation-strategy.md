# Validation Strategy

This project depends on a brittle mix of repository ingestion, Markdown parsing, optional OCR, PostgreSQL full-text search, Qdrant vector retrieval, TEI embeddings, optional reranking, local answer generation, and React evidence rendering. Validation must prove that the system returns grounded evidence when everything works and clearly reports degraded behavior when one stage fails.

## Coverage Map

| Area | Happy-path coverage | Fallback coverage | Current tests |
| --- | --- | --- | --- |
| Repository inventory | Discovers top-level directories, project files, README-style files, workflow paths, and license files with deterministic ordering. | Handles missing project files and fallback license names. | `tests/test_repo_inventory.py` |
| Markdown ingestion | Parses frontmatter, headings, stable anchors, canonical metadata, content type, license family, and deterministic chunk IDs. | Normalizes missing or partial metadata for older indexed rows. | `backend/tests/test_ingest_pipeline.py` |
| OCR and PDFs | Not implemented today. Future OCR tests must cover page-level provenance, confidence thresholds, image-only pages, timeout behavior, and skipped-page reporting. | OCR unavailable should not block Markdown ingestion and must never produce citations to unavailable scanned content. | Future `backend/tests/test_ocr_ingest.py` |
| Embeddings and vector upsert | Batches TEI-compatible embedding calls and idempotently upserts deterministic vector points. | Accepts TEI response variants and validates deterministic Qdrant/pgvector filters. | `backend/tests/test_vector_upsert.py` |
| Hybrid retrieval | Runs lexical and dense retrieval, merges with reciprocal rank fusion, applies metadata boosts, and preserves score breakdown fields. | Returns lexical-only, semantic-only, or fused-without-rerank results with structured warnings. | `backend/tests/test_recommendations.py` |
| Reranking | Reranks the fused top-k candidate pool and records final rank. | Retries reranker failures, falls back to fusion, and exposes `reranker_unavailable`. | `backend/tests/test_recommendations.py` |
| Claim-checking and recommendations | Produces grounded recommendation categories with direct evidence links. | Still emits resiliency recommendations when retrieval is degraded and evidence is partial. | `backend/tests/test_recommendations.py`, `backend/tests/test_api.py` |
| API serialization | Returns typed search, analyze, answer, health, metrics, and ingest responses. | Uses structured validation and service-not-configured errors; exposes `warnings` and `degraded`. | `backend/tests/test_api.py` |
| Evidence rendering | Builds result cards, answer sources, recommendation panels, filters, score explanations, and warning banners. | Displays degraded-mode warnings without hiding available evidence. | CI frontend build; future component tests |

## Required Local Checks

Run the full local regression suite before merging backend or retrieval changes:

```powershell
python -m pytest -p no:cacheprovider
```

Run the frontend build before merging UI changes:

```powershell
cd frontend
npm install
npm run build
```

Validate local orchestration before merging Docker or dependency changes:

```powershell
docker compose config --quiet
docker compose build api frontend
```

For retrieval behavior, add focused tests whenever a change affects ranking, filtering, source attribution, warning semantics, or score explanations. A good retrieval test should pin the query, candidate IDs, metadata, score inputs, final order, warnings, and source URLs.

## Golden Queries

Golden-query tests should be deterministic and small. They should avoid live network dependencies, use mocked lexical/vector/reranker responses, and assert both ranking quality and evidence quality.

Try these in the search box during local UI testing. They should exercise real relevance, reasoning, and evidence quality:

1. `How should I combine BM25 and semantic search for better relevance?`
2. `When should I use reranking after hybrid retrieval?`
3. `How do I improve search results for short keyword queries?`
4. `What is the best way to index documentation chunks with stable source links?`
5. `How can I reduce duplicate or overlapping search results?`
6. `What metadata should I store for filtering search results by repo and content type?`
7. `How do I evaluate whether retrieval quality improved?`
8. `What are recommended approaches for semantic search in Elasticsearch?`
9. `How should I handle ingestion updates when source documentation changes?`
10. `What can improve answer quality when search returns multiple similar docs?`

Recommended first smoke test:

```text
When should I use reranking after hybrid retrieval?
```

Start with these query families:

| Query | Expected behavior | Metrics |
| --- | --- | --- |
| `When should I use reranking after hybrid retrieval?` | Retrieves hybrid/reranking guidance, keeps direct Elastic source links, and reranks only the fused top-k set. | NDCG@10, MRR@10, Recall@20, source-link coverage |
| `How do I filter results by repository and license?` | Applies normalized `repo`, `path`, `content_type`, and `license_family` filters deterministically. | Filter precision, zero unexpected repos, stable ordering |
| `What happens if the reranker is unavailable?` | Returns fused results with `reranker_unavailable`, `degraded: true`, and no fabricated evidence. | Warning coverage, Recall@20 against fused baseline |
| `How should changed-source identifiers be mapped?` | Surfaces mapping recommendations with direct evidence and normalized metadata fields. | Recommendation category coverage, evidence count |
| `How do I index only new documentation changes?` | Explains incremental indexing with deterministic chunk IDs and content hashes. | Source attribution coverage, answer faithfulness |

Latency checks should record stage timings for lexical retrieval, query embedding, vector retrieval, RRF, reranking, answer synthesis, and UI response time. For local CPU-only development, reranking should be measured separately because model loading and cross-encoder inference dominate perceived latency.

## CI Matrix Proposal

Current CI runs backend tests, frontend build, Docker Compose validation, and an on-demand deterministic evaluation workflow. The next CI matrix should make dependency risk explicit:

| Job | Runtime | Services | Purpose |
| --- | --- | --- | --- |
| `backend-unit` | Python 3.12 | None | Fast parser, chunking, metadata, API, retrieval, fallback, and metric tests. |
| `frontend-build` | Node 22 | None | TypeScript and Vite build for evidence rendering and warning UI. |
| `compose-smoke` | Docker | PostgreSQL, Qdrant, API | Health, metrics, structured error responses, and startup dependency checks. |
| `retrieval-degraded` | Python 3.12 | Mocked TEI/Qdrant/Postgres failures | Verifies lexical-only, semantic-only, reranker-failed, and no-evidence semantics. |
| `eval-smoke` | Python 3.12 | Mocked retrieval fixtures | Runs golden queries and records NDCG@10, MRR@10, Recall@20, warning coverage, and source-link coverage. |
| `ocr-future` | Python 3.12 plus OCR toolchain | OCR fixture files | Once OCR exists, validates page provenance, skipped pages, confidence thresholds, and timeout handling. |

Every relevance-affecting pull request should describe the golden queries it changes, the expected ranking movement, and why source attribution remains correct. Dependency upgrades should include at least one fallback test for the upgraded component because vector stores, OCR engines, rerankers, and local LLM backends tend to fail in different ways across versions.

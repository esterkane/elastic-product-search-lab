# Relevance And Hybrid Retrieval

## API Strategies

The search API supports explicit retrieval strategies through `/search?strategy=...`:

| Strategy | Behavior |
| --- | --- |
| `baseline_bm25` | Strict BM25 over title, brand, category, description, and catalog text. |
| `boosted_bm25` | Existing default boosted lexical path with popularity, recency, policies, and cohorts. |
| `enriched_lexical` | Searches `search_profile`, `catalog_text`, and attributes with exact-match boosts. |
| `hybrid_rrf` | Elasticsearch RRF retriever combining enriched lexical and kNN vector retrieval. |
| `reranked` | First-stage hybrid when `queryVector` exists, otherwise enriched lexical, then local deterministic rerank. |

Hybrid retrieval requires a query vector:

```bash
curl "http://localhost:3000/search?q=quiet%20travel%20headphones&strategy=hybrid_rrf&queryVector=0.01,0.02,0.03&debug=true"
```

If no vector is supplied, `hybrid_rrf` falls back to `enriched_lexical` and the debug payload reports `executed: hybrid_fallback`.

## Exact-Match Precision

`enriched_lexical` and the lexical side of `hybrid_rrf` include exact-match clauses:

- exact `title.keyword`
- `match_phrase` on `title`
- exact `brand`
- exact `category`

These clauses protect SKU-like, brand, and exact product-name queries from being overpowered by vector similarity.

## Vector Fields

The catalog mapping includes `embedding` and `semantic_embedding` dense vector fields. The API defaults to `semantic_embedding`, and callers can pass `vectorField=embedding` for experiments.

The vector-producing service is intentionally not embedded inside the API yet. This keeps the API deterministic for tests and lets local scripts use either sentence-transformers or hash embeddings.

## Debug And Profile

`debug=true` enables:

- Elasticsearch `explain`
- Elasticsearch `_profile`
- returned query DSL or retriever request
- requested/executed strategy
- vector availability
- rerank status
- observed API-side latency
- policy/cohort debug information

## Suggest

Autocomplete remains separate from main retrieval:

```bash
curl "http://localhost:3000/suggest?q=wir&size=5&debug=true"
```

The suggest endpoint targets `product-suggest` by default and uses `search_as_you_type` fields. This keeps typeahead fast and avoids changing the main ranking query for every keystroke.

## Reports

Run the retrieval comparison report:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_hybrid_search.py `
  --index products-read `
  --provider hash `
  --rerank
```

Outputs:

- `reports/retrieval-strategy-report.json`
- `reports/retrieval-strategy-report.md`

The report compares baseline lexical, boosted lexical, enriched profile, hybrid RRF, and optional reranked strategies with Precision@10, MRR, nDCG@10, and per-strategy latency.

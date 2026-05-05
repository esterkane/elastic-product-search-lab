# Retrieval Strategy Report

Template artifact. Run `scripts/evaluate_hybrid_search.py` against a local Elasticsearch index to populate measured metrics.

Expected strategies:

- `baseline_lexical`
- `boosted_lexical`
- `enriched_profile`
- `hybrid_rrf`
- `reranked`

The generated report compares Precision@10, MRR, nDCG@10, and client-side latency. This template intentionally contains no benchmark claims.

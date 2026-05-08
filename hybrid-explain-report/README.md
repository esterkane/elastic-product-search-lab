# Hybrid Explain Report

This artifact generates a human-readable debugging report for difficult hybrid retrieval cases. It mirrors OpenSearch 2.19+ hybrid explain output by showing normalized lexical score, normalized semantic score, weighted score combination, metadata multiplier, failure category, and recommended fix.

## Run

```powershell
python scripts/generate_hybrid_explain.py
python -m pytest tests -p no:cacheprovider
```

Outputs:

- `reports/hybrid-explain-report.json`
- `reports/hybrid-explain-report.md`

## When To Use This Report

Use this report when the expected document is in the candidate set but the final hybrid ranking looks wrong. The score table helps separate four common failure modes:

- `lexical_miss`: BM25 misses synonyms, shorthand, or domain language.
- `semantic_miss`: embeddings over-match a nearby concept or miss domain-specific intent.
- `fusion_issue`: lexical and semantic channels disagree, and the configured weights pick the weaker result.
- `metadata_issue`: a relevant result is demoted by missing or incorrect metadata.

The goal is not a dashboard. It is a concise artifact for relevance reviews, incident debugging, and interview discussion.

## OpenSearch Explain Notes

OpenSearch hybrid explain was introduced in 2.19. It requires `explain=true` on the hybrid search request and a search pipeline that includes the `hybrid_score_explanation` response processor. The live OpenSearch response exposes normalization and score-combination details; this fixture keeps those concepts reproducible without requiring a running cluster.

References:

- https://docs.opensearch.org/docs/latest/vector-search/ai-search/hybrid-search/explain/
- https://docs.opensearch.org/docs/2.19/search-plugins/search-pipelines/explanation-processor/

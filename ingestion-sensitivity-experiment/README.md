# Ingestion Sensitivity Experiment

This experiment measures how deterministic ingestion defects change retrieval quality on a small product-support corpus.

It compares four index variants:

- `clean`: title, category, and body are indexed as expected.
- `missing_metadata`: title and category are dropped.
- `noisy_descriptions`: deterministic junk terms are injected into body text.
- `bad_chunking`: each document is split into two chunks, and the second chunk loses title context.

## Run

```powershell
python scripts/ingestion_sensitivity.py
python -m pytest tests -p no:cacheprovider
```

If `python` is not on PATH, use an explicit Python executable.

Outputs:

- `reports/ingestion-sensitivity-report.json`
- `reports/ingestion-sensitivity-report.md`

## Method

The evaluator uses a deterministic lexical scorer over title, category, and body fields. Judgments are graded per query, and variants are compared against the clean index with:

- nDCG@5
- MRR@5
- Precision@3
- Recall@5

The perturbation seed defaults to `30` so noisy descriptions are reproducible.

## Interpretation

This is a retrieval-quality smoke test, not a production-scale benchmark. The useful signal is directional: it shows which ingestion defects move ranked metrics and which queries are most sensitive to field loss, description noise, or chunk boundary mistakes.

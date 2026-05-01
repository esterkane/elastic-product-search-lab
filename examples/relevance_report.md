# Relevance Report

Offline evaluation for the local sample product catalog using graded relevance judgments.

## Why This Matters

This report gives a hiring reviewer a quick view of how search quality is measured. It shows per-query behavior, not just an aggregate score, because product search changes often help one query class while hurting another.

## Aggregate Metrics

| Metric | Value | What It Indicates |
| --- | ---: | --- |
| Precision@10 | 0.750 | Share of returned top-10 products judged relevant. |
| MRR | 0.750 | How quickly the first relevant product appears. |
| nDCG@10 | 0.576 | Ranking quality with graded relevance. |

## Per-Query Metrics

| Query | Precision@10 | MRR | nDCG@10 | Top Results |
| --- | ---: | ---: | ---: | --- |
| cast iron skillet | 1.000 | 1.000 | 0.861 | P100023 |
| espresso machine | 1.000 | 1.000 | 0.787 | P100017 |
| noise cancelling headphones | 0.000 | 0.000 | 0.000 | none |
| portable bluetooth speaker | 1.000 | 1.000 | 0.745 | P100022 |
| running shoes waterproof | 0.000 | 0.000 | 0.000 | none |
| usb c charger | 1.000 | 1.000 | 0.713 | P100018 |
| water bottle insulated | 1.000 | 1.000 | 0.787 | P100007 |
| wireless mouse | 1.000 | 1.000 | 0.713 | P100008 |

## Notes

Precision@10 counts relevant products in the top results but does not care where they appear. MRR rewards the first relevant product appearing early. nDCG@10 uses graded relevance, so exact matches are worth more than substitutes or complements.

The zero-result rows are useful, not embarrassing: they show where the sample catalog or query strategy needs more coverage.

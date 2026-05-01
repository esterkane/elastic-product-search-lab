# Reranking Report

Optional local reranking comparison using the deterministic placeholder reranker. This is a workflow demonstration, not an ML quality claim.

| Query | Strategy | nDCG@10 Before | nDCG@10 After | Delta | First Stage ms | Rerank ms | Total ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cast iron skillet | baseline_lexical | 0.861 | 0.861 | +0.000 | 44.6 | 0.0 | 44.7 |
| cast iron skillet | boosted_lexical | 0.861 | 0.861 | +0.000 | 44.6 | 0.0 | 44.6 |
| cast iron skillet | hybrid_rrf | 0.922 | 0.922 | +0.000 | 150.9 | 0.2 | 151.1 |
| espresso machine | baseline_lexical | 0.787 | 0.787 | +0.000 | 47.6 | 0.0 | 47.7 |
| espresso machine | boosted_lexical | 0.787 | 0.787 | +0.000 | 44.1 | 0.0 | 44.1 |
| espresso machine | hybrid_rrf | 0.787 | 1.000 | +0.213 | 153.2 | 0.3 | 153.5 |
| noise cancelling headphones | baseline_lexical | 0.787 | 0.787 | +0.000 | 45.8 | 0.0 | 45.8 |
| noise cancelling headphones | boosted_lexical | 0.787 | 0.787 | +0.000 | 47.8 | 0.0 | 47.8 |
| noise cancelling headphones | hybrid_rrf | 0.787 | 0.787 | +0.000 | 152.3 | 0.3 | 152.6 |
| portable bluetooth speaker | baseline_lexical | 0.745 | 0.745 | +0.000 | 46.9 | 0.0 | 46.9 |
| portable bluetooth speaker | boosted_lexical | 0.745 | 0.745 | +0.000 | 48.1 | 0.0 | 48.1 |
| portable bluetooth speaker | hybrid_rrf | 0.791 | 0.921 | +0.130 | 150.5 | 0.2 | 150.7 |
| running shoes waterproof | baseline_lexical | 0.000 | 0.000 | +0.000 | 46.9 | 0.0 | 46.9 |
| running shoes waterproof | boosted_lexical | 0.000 | 0.000 | +0.000 | 44.4 | 0.0 | 44.4 |
| running shoes waterproof | hybrid_rrf | 0.847 | 0.562 | -0.285 | 148.0 | 0.2 | 148.2 |
| usb c charger | baseline_lexical | 0.713 | 0.713 | +0.000 | 47.4 | 0.0 | 47.4 |
| usb c charger | boosted_lexical | 0.713 | 0.713 | +0.000 | 48.2 | 0.0 | 48.2 |
| usb c charger | hybrid_rrf | 0.844 | 0.930 | +0.085 | 150.8 | 0.2 | 151.0 |
| water bottle insulated | baseline_lexical | 0.787 | 0.787 | +0.000 | 47.7 | 0.0 | 47.8 |
| water bottle insulated | boosted_lexical | 0.787 | 0.787 | +0.000 | 47.7 | 0.0 | 47.8 |
| water bottle insulated | hybrid_rrf | 0.787 | 1.000 | +0.213 | 150.2 | 0.3 | 150.5 |
| wireless mouse | baseline_lexical | 0.713 | 0.713 | +0.000 | 44.6 | 0.0 | 44.6 |
| wireless mouse | boosted_lexical | 0.713 | 0.713 | +0.000 | 47.3 | 0.0 | 47.4 |
| wireless mouse | hybrid_rrf | 0.745 | 0.745 | +0.000 | 147.1 | 0.4 | 147.4 |

Average nDCG@10 delta: +0.015
p95 latency before rerank: 152.1 ms
p95 latency after rerank: 152.4 ms
Warning: relevance improved while p95 latency worsened. Review whether the tradeoff is acceptable.

# Product Search Relevance Report

Evaluated queries: 10
Baseline strategy: `baseline_bm25`

## Strategy Summary

| Strategy | Status | Evaluated Queries | Precision@5 | Recall@5 | MRR@10 | nDCG@10 | Delta nDCG@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_bm25 | ok | 10 | 0.200 | 0.067 | 0.200 | 0.149 | +0.000 |
| boosted_bm25 | ok | 10 | 0.600 | 0.333 | 0.600 | 0.526 | +0.377 |
| enriched_profile | ok | 10 | 0.683 | 0.600 | 0.800 | 0.733 | +0.584 |

## Per-Query Results

| Query | Strategy | Winner | Precision@5 | Recall@5 | MRR@10 | nDCG@10 | Top Results |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| wireless noise cancelling headphones | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| wireless noise cancelling headphones | boosted_bm25 | tie | 1.000 | 0.500 | 1.000 | 0.787 | P100002 |
| wireless noise cancelling headphones | enriched_profile | tie | 1.000 | 0.500 | 1.000 | 0.787 | P100002 |
| cheap running shoes | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| cheap running shoes | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| cheap running shoes | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| coffee machine with grinder | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| coffee machine with grinder | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| coffee machine with grinder | enriched_profile | yes | 0.500 | 1.000 | 1.000 | 1.000 | P100017, P100001, P100011, P100021 |
| laptop backpack waterproof | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| laptop backpack waterproof | boosted_bm25 | yes | 1.000 | 0.500 | 1.000 | 0.917 | P100003 |
| laptop backpack waterproof | enriched_profile |  | 0.333 | 0.500 | 1.000 | 0.917 | P100003, P100005, P100022 |
| gift for gamer | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| gift for gamer | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| gift for gamer | enriched_profile | yes | 1.000 | 1.000 | 1.000 | 0.815 | P100010, P100013, P100022 |
| organic baby food | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| organic baby food | boosted_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| organic baby food | enriched_profile |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| usb c laptop charger | baseline_bm25 |  | 1.000 | 0.333 | 1.000 | 0.745 | P100018 |
| usb c laptop charger | boosted_bm25 |  | 1.000 | 0.333 | 1.000 | 0.745 | P100018 |
| usb c laptop charger | enriched_profile | yes | 1.000 | 1.000 | 1.000 | 1.000 | P100018, P100013, P100008 |
| insulated stainless steel water bottle | baseline_bm25 |  | 1.000 | 0.333 | 1.000 | 0.745 | P100007 |
| insulated stainless steel water bottle | boosted_bm25 | tie | 1.000 | 0.667 | 1.000 | 0.947 | P100007, P100019 |
| insulated stainless steel water bottle | enriched_profile | tie | 1.000 | 0.667 | 1.000 | 0.947 | P100007, P100019 |
| cast iron pan for camping | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| cast iron pan for camping | boosted_bm25 | tie | 1.000 | 0.333 | 1.000 | 0.861 | P100023 |
| cast iron pan for camping | enriched_profile | tie | 1.000 | 0.333 | 1.000 | 0.861 | P100023 |
| waterproof ebook reader | baseline_bm25 |  | 0.000 | 0.000 | 0.000 | 0.000 | none |
| waterproof ebook reader | boosted_bm25 | tie | 1.000 | 1.000 | 1.000 | 1.000 | P100005 |
| waterproof ebook reader | enriched_profile | tie | 1.000 | 1.000 | 1.000 | 1.000 | P100005 |

## Notes

`search_profile` is deterministic ingestion-time text enrichment built from product fields. The `enriched_profile` strategy searches that field plus title/category/brand context.
Metrics are deterministic and use the checked-in judgment list under `data/judgments/product_search_judgments.json`.

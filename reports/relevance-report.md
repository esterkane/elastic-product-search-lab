# Product Search Relevance Report

Evaluated queries: 10

## Strategy Summary

| Strategy | Status | Evaluated Queries | Pending Queries | Precision@5 | Recall@5 | MRR@10 | nDCG@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_bm25 | ok | 10 | 0 | 0.200 | 0.067 | 0.200 | 0.149 |
| boosted_bm25 | ok | 10 | 0 | 0.600 | 0.333 | 0.600 | 0.526 |
| enriched_profile | pending | 0 | 10 | 0.000 | 0.000 | 0.000 | 0.000 |

## Per-Query Results

| Query | Strategy | Status | Precision@5 | Recall@5 | MRR@10 | nDCG@10 | Top Results | Note |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| wireless noise cancelling headphones | baseline_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| wireless noise cancelling headphones | boosted_bm25 | ok | 1.000 | 0.500 | 1.000 | 0.787 | P100002 |  |
| cheap running shoes | baseline_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| cheap running shoes | boosted_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| coffee machine with grinder | baseline_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| coffee machine with grinder | boosted_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| laptop backpack waterproof | baseline_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| laptop backpack waterproof | boosted_bm25 | ok | 1.000 | 0.500 | 1.000 | 0.917 | P100003 |  |
| gift for gamer | baseline_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| gift for gamer | boosted_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| organic baby food | baseline_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| organic baby food | boosted_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| usb c laptop charger | baseline_bm25 | ok | 1.000 | 0.333 | 1.000 | 0.745 | P100018 |  |
| usb c laptop charger | boosted_bm25 | ok | 1.000 | 0.333 | 1.000 | 0.745 | P100018 |  |
| insulated stainless steel water bottle | baseline_bm25 | ok | 1.000 | 0.333 | 1.000 | 0.745 | P100007 |  |
| insulated stainless steel water bottle | boosted_bm25 | ok | 1.000 | 0.667 | 1.000 | 0.947 | P100007, P100019 |  |
| cast iron pan for camping | baseline_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| cast iron pan for camping | boosted_bm25 | ok | 1.000 | 0.333 | 1.000 | 0.861 | P100023 |  |
| waterproof ebook reader | baseline_bm25 | ok | 0.000 | 0.000 | 0.000 | 0.000 | none |  |
| waterproof ebook reader | boosted_bm25 | ok | 1.000 | 1.000 | 1.000 | 1.000 | P100005 |  |
| wireless noise cancelling headphones | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| cheap running shoes | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| coffee machine with grinder | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| laptop backpack waterproof | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| gift for gamer | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| organic baby food | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| usb c laptop charger | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| insulated stainless steel water bottle | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| cast iron pan for camping | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |
| waterproof ebook reader | enriched_profile | pending | 0.000 | 0.000 | 0.000 | 0.000 | none | Pending: enriched_profile requires enriched product-profile fields in the index. |

## Notes

`enriched_profile` is included as a pending strategy until enriched product-profile fields are added to the index.
Metrics are deterministic and use the checked-in judgment list under `data/judgments/product_search_judgments.json`.

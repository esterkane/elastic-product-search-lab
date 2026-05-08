# Hybrid Explain Report

Generated: `2026-05-08T08:48:07.842620+00:00`

## Hybrid Configuration

- Normalization: `min_max`
- Combination: `weighted_arithmetic_mean`
- Lexical weight: `0.55`
- Semantic weight: `0.45`
- Top-k inspected: `3`

## Failure Summary

| Category | Count |
| --- | ---: |
| fusion_issue | 1 |
| lexical_miss | 1 |
| metadata_issue | 1 |
| no_failure | 1 |
| semantic_miss | 1 |

## Hard Query Explanations

### q-lexical-miss: ANC cans last all day

- Expected page: `doc-headphones-battery`
- Expected rank: `2`
- Failure category: `lexical_miss`
- Recommended fix: Add synonym expansion for ANC/cans/headphones and battery-life phrasing before BM25 retrieval.

| Rank | Doc | Lexical raw | Semantic raw | Lexical norm | Semantic norm | Metadata | Combined | Explanation |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | doc-headphones-codec | 0.340 | 0.410 | 1.000 | 0.206 | 1.00 | 0.643 | min_max lexical=1.000, min_max semantic=0.206, weighted_mean=0.643, metadata_multiplier=1.00 |
| 2 | doc-headphones-battery | 0.180 | 0.910 | 0.000 | 1.000 | 1.00 | 0.450 | min_max lexical=0.000, min_max semantic=1.000, weighted_mean=0.450, metadata_multiplier=1.00 |
| 3 | doc-power-bank | 0.220 | 0.280 | 0.250 | 0.000 | 0.40 | 0.055 | min_max lexical=0.250, min_max semantic=0.000, weighted_mean=0.138, metadata_multiplier=0.40 |

### q-semantic-miss: return muddy trail shoes

- Expected page: `doc-boots-waterproof`
- Expected rank: `2`
- Failure category: `semantic_miss`
- Recommended fix: Improve embeddings or add domain examples connecting trail shoes, hiking boots, mud, and return policy language.

| Rank | Doc | Lexical raw | Semantic raw | Lexical norm | Semantic norm | Metadata | Combined | Explanation |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | doc-boots-sizing | 0.620 | 0.730 | 0.559 | 1.000 | 1.00 | 0.758 | min_max lexical=0.559, min_max semantic=1.000, weighted_mean=0.758, metadata_multiplier=1.00 |
| 2 | doc-boots-waterproof | 0.880 | 0.310 | 1.000 | 0.000 | 1.00 | 0.550 | min_max lexical=1.000, min_max semantic=0.000, weighted_mean=0.550, metadata_multiplier=1.00 |
| 3 | doc-rain-jacket | 0.290 | 0.450 | 0.000 | 0.333 | 0.60 | 0.090 | min_max lexical=0.000, min_max semantic=0.333, weighted_mean=0.150, metadata_multiplier=0.60 |

### q-fusion-issue: espresso grinder cleaning tablets

- Expected page: `doc-grinder-cleaning`
- Expected rank: `2`
- Failure category: `fusion_issue`
- Recommended fix: Reduce semantic weight or add query-intent routing when exact maintenance terms appear.

| Rank | Doc | Lexical raw | Semantic raw | Lexical norm | Semantic norm | Metadata | Combined | Explanation |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | doc-grinder-settings | 0.610 | 0.920 | 0.536 | 1.000 | 1.00 | 0.745 | min_max lexical=0.536, min_max semantic=1.000, weighted_mean=0.745, metadata_multiplier=1.00 |
| 2 | doc-grinder-cleaning | 0.930 | 0.590 | 1.000 | 0.000 | 1.00 | 0.550 | min_max lexical=1.000, min_max semantic=0.000, weighted_mean=0.550, metadata_multiplier=1.00 |
| 3 | doc-espresso-scale | 0.240 | 0.660 | 0.000 | 0.212 | 0.70 | 0.067 | min_max lexical=0.000, min_max semantic=0.212, weighted_mean=0.095, metadata_multiplier=0.70 |

### q-metadata-issue: usb c backpack warranty defects

- Expected page: `doc-backpack-warranty`
- Expected rank: `1`
- Failure category: `metadata_issue`
- Recommended fix: Repair category metadata and boost policy/warranty content type for warranty-intent queries.

| Rank | Doc | Lexical raw | Semantic raw | Lexical norm | Semantic norm | Metadata | Combined | Explanation |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | doc-backpack-warranty | 0.810 | 0.840 | 1.000 | 1.000 | 0.20 | 0.200 | min_max lexical=1.000, min_max semantic=1.000, weighted_mean=1.000, metadata_multiplier=0.20 |
| 2 | doc-power-bank | 0.570 | 0.610 | 0.250 | 0.000 | 1.00 | 0.137 | min_max lexical=0.250, min_max semantic=0.000, weighted_mean=0.137, metadata_multiplier=1.00 |
| 3 | doc-backpack-capacity | 0.490 | 0.670 | 0.000 | 0.261 | 1.00 | 0.117 | min_max lexical=0.000, min_max semantic=0.261, weighted_mean=0.117, metadata_multiplier=1.00 |

### q-balanced-win: waterproof shell for wet hikes

- Expected page: `doc-rain-jacket`
- Expected rank: `1`
- Failure category: `no_failure`
- Recommended fix: No immediate fix; this is a control query where lexical and semantic channels agree.

| Rank | Doc | Lexical raw | Semantic raw | Lexical norm | Semantic norm | Metadata | Combined | Explanation |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | doc-rain-jacket | 0.860 | 0.880 | 1.000 | 1.000 | 1.00 | 1.000 | min_max lexical=1.000, min_max semantic=1.000, weighted_mean=1.000, metadata_multiplier=1.00 |
| 2 | doc-boots-waterproof | 0.520 | 0.640 | 0.433 | 0.510 | 0.70 | 0.328 | min_max lexical=0.433, min_max semantic=0.510, weighted_mean=0.468, metadata_multiplier=0.70 |
| 3 | doc-boots-sizing | 0.260 | 0.390 | 0.000 | 0.000 | 0.50 | 0.000 | min_max lexical=0.000, min_max semantic=0.000, weighted_mean=0.000, metadata_multiplier=0.50 |

## Troubleshooting Use

Use this report when a hybrid result looks wrong but the top-k set still contains the expected document. The breakdown separates missing lexical vocabulary, weak semantic similarity, score-fusion imbalance, and metadata penalties so fixes can target the failing stage.

## Verification Notes

OpenSearch hybrid explain supports `explain=true` on hybrid searches when the search pipeline includes the `hybrid_score_explanation` response processor. The fixture mirrors those explain fields with normalized lexical score, normalized semantic score, combination result, and metadata multiplier.

# Ingestion Sensitivity Experiment

Generated: `2026-05-08T08:12:37.862096+00:00`
Seed: `30`
Documents: `12`

## Variant Metrics

| Variant | Chunks | nDCG@5 | MRR@5 | Precision@3 | Recall@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| clean | 12 | 0.987 | 1.000 | 0.917 | 0.917 |
| missing_metadata | 12 | 0.987 | 1.000 | 0.917 | 0.917 |
| noisy_descriptions | 12 | 0.979 | 1.000 | 0.833 | 0.917 |
| bad_chunking | 24 | 0.971 | 1.000 | 0.833 | 0.833 |

## Deltas Vs Clean

| Variant | nDCG@5 delta | MRR@5 delta | Precision@3 delta | Recall@5 delta |
| --- | ---: | ---: | ---: | ---: |
| missing_metadata | +0.000 | +0.000 | +0.000 | +0.000 |
| noisy_descriptions | -0.008 | +0.000 | -0.083 | +0.000 |
| bad_chunking | -0.015 | +0.000 | -0.083 | -0.083 |

## Interpretation

bad_chunking caused the largest nDCG@5 drop because bad chunk boundaries split context and create weaker fragments.

## Per Query Effects

### clean

| Query | Top result | nDCG@5 | Ranked ids |
| --- | --- | ---: | --- |
| q-headphones | doc-headphones-battery | 1.000 | doc-headphones-battery, doc-headphones-codec, doc-headphones-fit |
| q-boots | doc-boots-waterproof | 1.000 | doc-boots-waterproof, doc-rain-jacket, doc-boots-sizing |
| q-grinder | doc-grinder-cleaning | 1.000 | doc-grinder-cleaning, doc-grinder-settings, doc-espresso-scale |
| q-backpack | doc-backpack-warranty | 0.947 | doc-backpack-warranty, doc-backpack-capacity, doc-headphones-battery, doc-headphones-codec |

### missing_metadata

| Query | Top result | nDCG@5 | Ranked ids |
| --- | --- | ---: | --- |
| q-headphones | doc-headphones-battery | 1.000 | doc-headphones-battery, doc-headphones-codec, doc-headphones-fit |
| q-boots | doc-boots-waterproof | 1.000 | doc-boots-waterproof, doc-boots-sizing, doc-rain-jacket |
| q-grinder | doc-grinder-cleaning | 1.000 | doc-grinder-cleaning, doc-grinder-settings, doc-espresso-scale |
| q-backpack | doc-backpack-warranty | 0.947 | doc-backpack-warranty, doc-backpack-capacity, doc-headphones-battery, doc-headphones-codec |

### noisy_descriptions

| Query | Top result | nDCG@5 | Ranked ids |
| --- | --- | ---: | --- |
| q-headphones | doc-headphones-battery | 1.000 | doc-headphones-battery, doc-headphones-fit, doc-headphones-codec, doc-rain-jacket, doc-power-bank |
| q-boots | doc-boots-waterproof | 0.970 | doc-boots-waterproof, doc-espresso-scale, doc-boots-sizing, doc-headphones-fit, doc-rain-jacket |
| q-grinder | doc-grinder-cleaning | 1.000 | doc-grinder-cleaning, doc-grinder-settings, doc-espresso-scale, doc-headphones-codec, doc-power-bank |
| q-backpack | doc-backpack-warranty | 0.947 | doc-backpack-warranty, doc-backpack-capacity, doc-grinder-cleaning, doc-boots-sizing, doc-headphones-fit |

### bad_chunking

| Query | Top result | nDCG@5 | Ranked ids |
| --- | --- | ---: | --- |
| q-headphones | doc-headphones-battery | 0.939 | doc-headphones-battery, doc-headphones-fit |
| q-boots | doc-boots-waterproof | 1.000 | doc-boots-waterproof, doc-rain-jacket, doc-boots-sizing |
| q-grinder | doc-grinder-cleaning | 1.000 | doc-grinder-cleaning, doc-grinder-settings, doc-espresso-scale |
| q-backpack | doc-backpack-warranty | 0.947 | doc-backpack-warranty, doc-backpack-capacity, doc-headphones-battery, doc-headphones-codec |

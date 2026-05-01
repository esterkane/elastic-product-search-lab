# Keyword vs Hybrid Retrieval

This example compares the current keyword BM25 baseline with future hybrid retrieval. The project has not implemented vector retrieval yet, so the hybrid notes are hypotheses to test once embeddings and judged query sets are available.

## Query: wireless mouse

Baseline keyword behavior:

- Strong title match should surface products like `Logitech MX Master 3S Wireless Mouse`.
- Brand/category boosts help if the user adds `logitech` or filters to computer accessories.
- Popularity should only break ties between similarly relevant mouse products.

Future hybrid expectation:

- Hybrid retrieval may help with synonyms such as `cordless mouse` or `ergonomic bluetooth pointer`.
- It should not outrank exact `wireless mouse` title matches unless offline metrics prove the semantic match is better.

## Query: noise cancelling headphones

Baseline keyword behavior:

- Title matches on `noise canceling headphones` should rank highly even with spelling variation between `canceling` and `cancelling`.
- Brand filters such as `Sony` should narrow the candidate set rather than act as soft hints.

Future hybrid expectation:

- Embeddings may improve recall for `ANC headset` or `quiet travel headphones`.
- Evaluation should check that speakers or unrelated audio accessories do not drift into the top results.

## Query: usb c charger

Baseline keyword behavior:

- Products with `USB-C`, `charger`, and high-wattage charging language should match through title, description, and catalog text.
- Exact title matches should beat broad electronics items that mention USB-C only as an accessory detail.

Future hybrid expectation:

- Hybrid retrieval may connect `laptop power bank` or `phone fast charging brick` to relevant products.
- Popularity boosting must be watched carefully because generic chargers are often more popular than niche but exact products.

## Query: running shoes waterproof

Baseline keyword behavior:

- Keyword search requires the product text to mention running shoes and waterproof-related language.
- If the catalog lacks waterproof attributes, lexical recall will be weak.

Future hybrid expectation:

- Hybrid retrieval may retrieve trail shoes or weather-resistant running footwear even when exact words differ.
- Offline judgments are essential here because semantic expansion can accidentally retrieve hiking boots or casual sneakers.

## Comparison Pattern

For each query, compare:

- Top 10 BM25 results.
- Top 10 boosted BM25 results.
- Future top 10 hybrid results.
- nDCG@10, MRR, and Precision@10.
- Query-level notes explaining wins and regressions.
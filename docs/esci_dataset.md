# Amazon ESCI Dataset

The Amazon ESCI dataset is a public product-search relevance benchmark. It provides query-product pairs with ESCI relevance labels: Exact, Substitute, Complement, and Irrelevant. Those labels map naturally to the lab's graded relevance scale:

- `Exact` or `E` -> `3`
- `Substitute` or `S` -> `2`
- `Complement` or `C` -> `1`
- `Irrelevant` or `I` -> `0`

## Why It Is Relevant

The dataset is useful for product search because it contains shopper-style queries, product metadata, and query-product relevance judgments. That combination supports offline ranking evaluation with metrics such as nDCG@10, MRR, and Precision@10.

The lab keeps sample data tiny by default, but ESCI gives the project a path toward a realistic relevance benchmark without inventing every judgment by hand.

## Download Separately

Do not commit the full ESCI dataset to this repository. Download it separately from the upstream Amazon Science/GitHub source and keep local raw files under `data/raw/`, which is ignored by Git.

Typical local layout:

```text
data/raw/esci/shopping_queries_dataset_products.parquet
data/raw/esci/shopping_queries_dataset_examples.parquet
```

## Preparing a Lightweight Sample

After downloading the raw files locally, install parquet support if needed and generate small JSONL files for this lab:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[esci]"
.\.venv\Scripts\python.exe scripts\prepare_esci_sample.py `
  --products data\raw\esci\shopping_queries_dataset_products.parquet `
  --examples data\raw\esci\shopping_queries_dataset_examples.parquet `
  --max-queries 100 `
  --max-products 1000
```

The script writes:

```text
data/generated/esci_products.jsonl
data/generated/esci_judgments.jsonl
```

Then load and evaluate them:

```powershell
.\.venv\Scripts\python.exe scripts\create_index.py --recreate
.\.venv\Scripts\python.exe scripts\load_sample_data.py --input data\generated\esci_products.jsonl
.\.venv\Scripts\python.exe scripts\evaluate_search.py --judgments data\generated\esci_judgments.jsonl
```

## Lightweight Repo Policy

Only small sample or generated demonstration files should be committed. Full raw parquet or CSV dataset files should stay local in `data/raw/` so the repository remains lightweight and GitHub-friendly.
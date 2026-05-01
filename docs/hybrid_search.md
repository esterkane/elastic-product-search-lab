# Hybrid Search

Hybrid search combines lexical retrieval with semantic vector retrieval. In this lab, lexical search uses BM25 over product fields, while semantic retrieval uses the existing `embedding` dense vector field with 384 dimensions.

## Lexical Retrieval

Lexical search is excellent for exact terms, brands, model names, category words, and SKU-like language. If a shopper searches `Sony headphones`, exact title and brand matches should matter a lot.

## Semantic Retrieval

Semantic retrieval uses embeddings to retrieve products with similar meaning even when the exact words differ. It can help vague or paraphrased queries such as `quiet travel headphones`, `cordless pointer`, or `laptop power bank`.

## Why Product Search Often Needs Both

Product search has both exact and fuzzy intent. Some shoppers know the exact brand or product family; others describe a need. Lexical retrieval protects precision for exact queries, while vector retrieval can improve recall for language mismatch.

## Where Semantic Search Can Hurt

Semantic retrieval can hurt exact SKU, brand, or compatibility queries. A vector model may decide two products are conceptually close even when one is the wrong brand, size, connector, or accessory type. That is why hybrid results must be evaluated for both improvements and regressions.

## RRF Fusion

Reciprocal Rank Fusion combines ranked lists by giving each product a score based on its rank in each list. A product that ranks well in both lexical and vector results rises, while a product that appears in only one list can still be considered. This lab implements local RRF so it does not depend on a specific Elasticsearch retriever syntax.

If the local Elasticsearch version supports RRF retrievers, `hybrid_search.py` also exposes an Elasticsearch retriever query shape as an implementation path. The local RRF path remains the default because it is easier to test and debug.

## Performance Tradeoffs

Hybrid search costs more than lexical search. It needs embedding generation, vector storage, kNN retrieval, and a fusion step. Latency, memory, and indexing cost all increase. The evaluation script reports latency per strategy so quality improvements can be weighed against runtime cost.

## Optional Setup

The project can use `sentence-transformers/all-MiniLM-L6-v2`, a compact 384-dimensional model. Install it only when you want real semantic embeddings:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[vector]"
```

Without that dependency, scripts fall back to deterministic hash embeddings so local demos and tests still run without paid APIs or cloud credentials.
# Kibana Search Demo: Outcomes and Interpretation

This page summarizes the Kibana Dev Tools queries captured during the local ESCI dataset test. It is meant as a portfolio walkthrough: what the index contains, how fields are modeled, how search behavior changes with enrichment, and how to troubleshoot relevance and latency using Elasticsearch-native tools.

The captured run used:

- Index: `products-v1`
- Documents: `1,215,851`
- Store size: about `3.1gb`
- Runtime: local single-node Elasticsearch
- Security: enabled, authenticated as `elastic`

## 1. Index Scale and Local Runtime

Outcome:

- `products-v1` is present and queryable.
- The index contains `1,215,851` documents from the local ESCI import.
- Health is `yellow`, which is expected for this single-node setup because the index has a replica configured but no second node to allocate it.
- The dataset size is large enough to make relevance and latency observations meaningful for a lab.

<details>
<summary>Query: show product index size</summary>

```http
GET _cat/indices/products-v1?v
```

</details>

Captured result:

```text
health status index       pri rep docs.count docs.deleted store.size
yellow open   products-v1   1   1    1215851            0      3.1gb
```

Interpretation:

This establishes that the project is not only a toy 25-row sample. The local Elasticsearch instance is holding a realistic product-search corpus, while still remaining small enough to run on a development machine.

## 2. Mapping Choices

Outcome:

The mapping shows field types chosen for product-search behavior, not just generic storage.

| Field | Type | Why It Matters |
| --- | --- | --- |
| `product_id` | `keyword` | Stable exact ID for deterministic updates and product lookup. |
| `title` | `text` + `keyword` subfield | Full-text relevance on title, plus exact/facet-safe representation when needed. |
| `brand` | `keyword` | Brand should be filtered/faceted exactly, not tokenized like body text. |
| `category` | `keyword` | Category is a filter/facet dimension. |
| `attributes` | `flattened` | Flexible product facts without mapping explosion. |
| `price` | `scaled_float` | Range filtering with controlled decimal precision. |
| `availability` | `keyword` | Availability should constrain results, not act as a scoring term. |
| `catalog_text` | `text` | Combined searchable product text. |
| `search_profile` | `text` | Deterministic enrichment field for intent-bearing search text. |
| `embedding` | `dense_vector` | Optional vector/hybrid retrieval experiments. |

<details>
<summary>Query: inspect relevant field mappings</summary>

```http
GET products-v1/_mapping/field/product_id,title,brand,category,attributes,price,availability,catalog_text,search_profile,embedding
```

</details>

Interpretation:

The captured mapping validates the core modeling decisions. Text fields are used where analysis and scoring are needed. Keyword fields are used where exact matching, filtering, and aggregations are expected. `flattened` keeps arbitrary product attributes manageable. `search_profile` is intentionally modeled as `text` because it is searched semantically through normal lexical analysis, not faceted.

## 3. Baseline Search vs Enriched Search

Query tested: `gift for gamer`

Outcome:

| Strategy | Took | Top Result Pattern | What It Shows |
| --- | ---: | --- | --- |
| Baseline BM25 | `24ms` | Gamer mugs, tumblers, shirts | Fast lexical matching over product fields. |
| Enriched profile | `183ms` | Gamer apparel with explicit gift/use-case language in `search_profile` | Ingestion enrichment exposes intent-oriented text. |

The enriched query returns documents where `search_profile` includes phrases such as `Great video game gift`, `Cool gifts for gamers`, `Birthday`, `Christmas`, and `Perfect gamer tees`. That makes the result explanation easier for a reviewer to understand: the indexed document carries richer searchable evidence.

<details>
<summary>Query: enriched search using search_profile</summary>

```http
GET products-v1/_search
{
  "size": 5,
  "_source": ["product_id", "title", "brand", "search_profile"],
  "query": {
    "multi_match": {
      "query": "gift for gamer",
      "fields": ["search_profile^3", "title^2", "category^1.5", "brand", "description^0.5"],
      "operator": "or",
      "minimum_should_match": "2<70%",
      "fuzziness": "AUTO"
    }
  }
}
```

</details>

<details>
<summary>Query: baseline lexical search</summary>

```http
GET products-v1/_search
{
  "size": 5,
  "_source": ["product_id", "title", "brand"],
  "query": {
    "multi_match": {
      "query": "gift for gamer",
      "fields": ["title^3", "brand^2", "description", "catalog_text"]
    }
  }
}
```

</details>

Interpretation:

This is the clearest Kibana-only example of the project thesis: search quality can be improved by improving indexed data quality, not only by changing query boosts. The enriched version is slower in this single run, so it should be evaluated with both relevance metrics and latency gates rather than adopted blindly.

## 4. Filtered Product Search

Query tested: `wireless headphones`

Outcome:

- Search returned strong product-title matches such as kids wireless headphones, Bose SoundSport wireless headphones, and sport/waterproof wireless headphones.
- `availability` was returned as `in_stock`.
- The query took `47ms` in the captured run.

<details>
<summary>Query: BM25 search with availability filter context</summary>

```http
GET products-v1/_search
{
  "size": 3,
  "_source": ["product_id", "title", "brand", "availability"],
  "query": {
    "bool": {
      "must": {
        "multi_match": {
          "query": "wireless headphones",
          "fields": ["title^3", "brand^2", "description", "catalog_text"]
        }
      },
      "filter": [
        { "term": { "availability": "in_stock" } }
      ]
    }
  }
}
```

</details>

Interpretation:

This demonstrates the difference between scoring and filtering. The textual query decides relevance. Availability constrains eligibility without changing term scoring. That is normally the right behavior for product search: out-of-stock status should not make a product more or less textually relevant; it should determine whether it is eligible.

## 5. Explain API for Relevance Debugging

Document tested: `B07PV42J92`

Outcome:

- `_explain` returned `matched: true`.
- The score was `47.270813`.
- The matching product was `Nenos Bluetooth Kids Headphones Wireless Kids Headphones...`.

<details>
<summary>Query: explain why one product matched</summary>

```http
GET products-v1/_explain/B07PV42J92
{
  "query": {
    "multi_match": {
      "query": "wireless headphones",
      "fields": ["title^3", "brand^2", "description", "catalog_text"]
    }
  }
}
```

</details>

Interpretation:

`_explain` is useful when a stakeholder asks why a specific product ranked. It exposes the scoring mechanics: which terms matched, which fields contributed, and how boosts affected the final score. This is a practical relevance-debugging workflow, not only a black-box API response.

## 6. Search Profiling for Latency Debugging

Query tested: `wireless headphones`

Outcome:

- The profiled multi-match query took `37ms`.
- The profile section showed a `DisjunctionMaxQuery` over `catalog_text`, `description`, boosted `title`, and boosted `brand`.
- The main query section reported `time_in_nanos: 28516676`, about `28.5ms`.
- The profile output showed match counts, scorer construction, scoring time, collector time, and fetch time.

<details>
<summary>Query: profile multi-field product search</summary>

```http
GET products-v1/_search
{
  "profile": true,
  "size": 5,
  "_source": ["product_id", "title"],
  "query": {
    "multi_match": {
      "query": "wireless headphones",
      "fields": ["title^3", "brand^2", "description", "catalog_text"]
    }
  }
}
```

</details>

Interpretation:

The profile view separates query execution from fetch work. This matters because a slow search may be slow due to query planning/scoring, collector work, or fetching large `_source` fields. In the captured run, the search is healthy for local development, but the output shows where a real investigation would start.

## 7. Safer Query Shape for a Broad Term

Query tested: `wireless`

Outcome:

- The fixed `match` query took `23ms`.
- The profile showed a simple `TermQuery` on `catalog_text:wireless`.
- Returned results included wireless chargers, wireless doorbells, wireless earbuds, and wireless headphones.

<details>
<summary>Query: fixed analyzed match query</summary>

```http
GET products-v1/_search
{
  "profile": true,
  "size": 20,
  "_source": ["product_id", "title"],
  "query": {
    "match": {
      "catalog_text": "wireless"
    }
  }
}
```

</details>

Interpretation:

This is a safer query shape for text search because it uses the inverted index produced by analysis. It is broad, so result quality still depends on better query intent, field boosts, filters, and ranking strategy, but the access pattern is much healthier than scanning-like patterns such as leading wildcards on large text fields.

## 8. Bad Aggregation: Text Field Used Like a Facet

Outcome:

- Aggregating on `title` failed with HTTP `400`.
- Elasticsearch explained that fielddata is disabled on `title`.
- The error explicitly recommends using a keyword field instead.

<details>
<summary>Query: intentionally bad aggregation on text field</summary>

```http
GET products-v1/_search
{
  "size": 0,
  "aggs": {
    "brands": {
      "terms": {
        "field": "title"
      }
    }
  }
}
```

</details>

Captured failure:

```text
Fielddata is disabled on [title] in [products-v1]. Text fields are not optimised for operations that require per-document field data like aggregations and sorting, so these operations are disabled by default. Please use a keyword field instead.
```

The correct pattern is to aggregate on a `keyword` field:

<details>
<summary>Query: correct aggregation on keyword field</summary>

```http
GET products-v1/_search
{
  "size": 0,
  "aggs": {
    "brands": {
      "terms": {
        "field": "brand"
      }
    }
  }
}
```

</details>

Interpretation:

This is a strong mapping lesson. `text` fields are for analyzed search. `keyword` fields are for exact values, filters, sorting, and aggregations. Enabling fielddata on `title` would be a risky workaround because it can use significant heap. The correct fix is to model facet fields as `keyword` or use an existing keyword subfield such as `title.keyword` where appropriate.

## Screenshot Checklist

Use these screenshots to tell the project story through Kibana only:

1. `_cat/indices/products-v1?v` showing 1.2M documents.
2. Field mapping query showing `keyword`, `text`, `flattened`, `scaled_float`, and `dense_vector`.
3. Baseline `gift for gamer` result.
4. Enriched `gift for gamer` result showing `search_profile`.
5. `_explain` for `B07PV42J92`.
6. `_profile` output for `wireless headphones`.
7. Text-field aggregation failure on `title` and the corrected `brand` aggregation.

## What This Demonstrates

The Kibana workflow demonstrates the core search-engineering loop:

- Model fields according to their search behavior.
- Index enriched product text when raw catalog fields are not enough.
- Compare query strategies with visible evidence.
- Use `_explain` for relevance debugging.
- Use `_profile` for latency troubleshooting.
- Treat field type errors as useful feedback about data modeling.


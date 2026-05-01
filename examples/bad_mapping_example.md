# Bad Mapping Example

Mapping mistakes can make relevance worse before ranking logic even runs. This lab keeps mappings small so these failure modes are easy to see.

## Bad: Product IDs as Text

If `product_id` is mapped as `text`, Elasticsearch tokenizes identifiers. Exact updates and lookups become fragile, and deterministic ingestion can accidentally fail to target the intended document. Product IDs should be `keyword`.

## Bad: Brand and Category as Only Text

If `brand` and `category` are only `text`, filters and facets become unreliable. A brand like `The Ordinary` can be tokenized into separate words, and category aggregations can fragment. These fields should be `keyword` with a lowercase normalizer for consistent filtering.

## Bad: Attributes Exploded Into Many Static Fields

Product attributes vary heavily by category. A mapping with thousands of explicit attribute fields can become sparse and hard to evolve. `flattened` is a practical first choice for a lab because it can store flexible key-value attributes without constant mapping churn.

## Bad: Dense Vector Dimensions Changed In Place

Changing an embedding field from one dimension count to another requires a new index. A `dense_vector` with `dims: 384` cannot safely become `dims: 768` in place. Versioned indexes and reindexing are the safer migration path.

## Bad: Popularity as the Primary Ranking Field

Popularity is not a mapping type mistake, but it is a relevance modeling mistake when treated as the main score. If popularity dominates BM25, exact niche products can disappear below generic best sellers. Popularity should be a mild boost and measured with offline metrics.
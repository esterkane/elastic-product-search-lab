# Mapping Decisions

The product index mapping is intentionally compact and production-inspired. It keeps the fields needed for common e-commerce relevance experiments while avoiding analyzer complexity that would distract from the lab's first search and evaluation workflows.

The index name is controlled by the `PRODUCT_INDEX` environment variable and defaults to `products-v1` in the index creation script.

## Field Choices

`product_id` is a `keyword` because it is an exact identifier. It should be filtered, joined to source catalog systems, and used for updates without tokenization.

`title` and `description` are `text` fields because users search with words, partial phrases, and natural product descriptions. The standard analyzer is enough for the first demo because it provides predictable tokenization without hiding relevance decisions behind custom analysis. `title` also has a `keyword` subfield for exact matching, sorting experiments, and diagnostics.

`brand` and `category` are `keyword` fields because they are structured facets and filters. They use a lowercase normalizer so values like `Sony` and `sony` can aggregate consistently while preserving exact-match behavior.

`attributes` is `flattened` because product attributes vary widely by category. A laptop, shoe, and coffee machine all have different attribute keys; `flattened` lets the lab store that flexible key-value shape without creating a large, sparse mapping for every possible attribute.

`price` uses `scaled_float` with a scaling factor of `100` so currency-style decimal prices can be stored efficiently while retaining cent-level precision for demo data.

`source_versions` is `flattened` so ingestion can record source-specific version markers, event IDs, or timestamps without requiring a mapping update for each upstream system.

`updated_at` and `indexed_at` are `date` fields to support freshness diagnostics, ingestion lag checks, and future recency features.

`catalog_text` is a broad `text` field for experiments that combine searchable product content into one field. It should not replace fielded relevance tuning, but it is useful for baselines.

`embedding` is a `dense_vector` with `384` dimensions, indexing enabled, and cosine similarity. The 384-dimensional shape matches common compact sentence-transformer style embeddings and keeps local hybrid retrieval experiments small enough for a development cluster.

## Reindexing and Safe Migration

Many mapping changes require reindexing because Elasticsearch cannot safely change how existing indexed values are represented. Examples include changing a field type, changing analyzers or normalizers for an existing field, changing dense vector dimensions, or moving a field from `text` to `keyword`.

Safe production migrations usually create a new versioned index, write documents into the new mapping, validate search behavior, and then move an alias. In this lab, `products-v1` makes that versioning explicit from the start.

Adding a new field is usually safer than changing an existing one, but it still needs a migration plan. The application must tolerate old documents that do not have the field, ingestion must populate it for new or reindexed documents, and relevance evaluation should confirm that ranking behavior has not regressed.

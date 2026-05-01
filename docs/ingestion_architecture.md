# Ingestion Architecture

The ingestion pipeline will model how product catalog records become search documents.

Planned stages:

- Source record loading.
- Schema validation and normalization.
- Search document transformation.
- Bulk indexing.
- Change-event simulation for create, update, delete, price, and availability events.

# Performance and Resilience

This lab runs Elasticsearch as a single local node so the search workflow is easy to inspect and repeat. That setup is useful for development, mapping experiments, ingestion tests, and relevance evaluation, but it is not a production topology.

## Local Single-Node Scope

The local runtime disables security and runs one node with a named Docker volume. That keeps portfolio and demo usage simple: there is no certificate setup, no credential handling, and no distributed cluster coordination to explain before the search work is visible.

The tradeoff is that a single node cannot validate production behavior around replication, shard allocation, rolling deploys, node loss, cross-zone networking, or operational security. Local results should be treated as directional, especially for latency and indexing throughput.

## Production Differences

A production product-search cluster would use security by default, dedicated credentials, TLS, role-based access, backups, monitoring, alerting, and a multi-node topology sized around query load, indexing volume, retention, and availability targets.

Production planning would also revisit:

- Primary and replica shard counts.
- Index lifecycle and versioned reindexing.
- Hot/warm storage choices where relevant.
- Snapshot and restore strategy.
- Capacity for peak catalog update windows.
- Query isolation, circuit breakers, and request timeouts.
- Deployment automation and safe rollback paths.

## Runtime Signals to Watch

The local Compose file uses a 6 GB Elasticsearch heap to leave room for realistic indexing and search experiments. Heap size is only one part of runtime health; the lab notes should also track garbage collection pauses, indexing pressure, bulk queue depth, rejected requests, and search latency percentiles.

Useful signals include:

- Heap usage and garbage collection frequency.
- Indexing pressure and bulk request rejections.
- Search thread pool queue size and rejected requests.
- Refresh cost during ingestion-heavy workloads.
- Segment count and merge pressure.
- p50, p95, and p99 search latency by query type.

## Why Tail Latency Matters

Average latency can hide the incidents users actually feel. Search systems often fail at the tail: a small percentage of slow queries can come from expensive filters, uneven shards, merge pressure, cache misses, overloaded queues, or noisy indexing bursts.

For product search, p95 and p99 latency are usually more useful than averages during incident review because they show whether the worst normal user experiences are getting worse. A ranking change that leaves average latency stable but doubles p99 may still be unsafe for a marketplace search experience.

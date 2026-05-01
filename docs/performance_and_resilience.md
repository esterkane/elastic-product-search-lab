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

## Why Averages Hide Incidents

Average latency can hide the incidents users actually feel. Search systems often fail at the tail: a small percentage of slow queries can come from expensive filters, uneven shards, merge pressure, cache misses, overloaded queues, or noisy indexing bursts.

For product search, p95 and p99 latency are usually more useful than averages during incident review because they show whether the worst normal user experiences are getting worse. A ranking change that leaves average latency stable but doubles p99 may still be unsafe for a marketplace search experience.

## Quality and Latency Together

Search quality and latency need to be reviewed together. Offline metrics such as nDCG@10, MRR, and Precision@10 can show that a boosted or hybrid strategy improves relevance, while the benchmark report can show whether that same strategy increases tail latency. A change that improves nDCG by a small amount but creates a sustained p99 regression should be treated as risky until the query plan, vector retrieval cost, or concurrency profile is understood.

The local benchmark writes `data/generated/performance_report.json` and `examples/performance_report.md`. Those files make it easy to compare baseline lexical, boosted lexical, and optional hybrid retrieval on the same query set.

## Paging Versus Dashboards

Some signals should page an operator because users may already be affected:

- High API error rate.
- Sustained p99 latency regression for critical search traffic.
- Search request timeouts.
- Elasticsearch rejected requests.
- Cluster health red.

Other signals usually belong on dashboards first because they are early warnings or lower-severity changes:

- Mild p95 drift.
- Cache hit ratio changes.
- Slower non-critical query class.
- Gradual heap pressure increase without rejections.
- Short-lived indexing queue growth during expected catalog loads.

## Resilience Patterns

Circuit breakers stop an unhealthy dependency from consuming all worker time. In a search API, a circuit breaker can fail fast when Elasticsearch is timing out repeatedly, giving the service a chance to recover and giving callers a consistent degraded response.

Bulkheads isolate resource pools so one workload cannot starve another. Search traffic, indexing traffic, embedding generation, and offline benchmarks should not all share unlimited concurrency against the same cluster.

Bounded concurrency keeps the API from launching more in-flight Elasticsearch requests than the cluster can handle. It is better to reject or shed excess load predictably than to allow queues to grow until every request is slow.

Exponential backoff with jitter is important for retries. Retrying immediately after a `429`, `503`, or connection timeout can amplify overload. Jitter prevents many workers from retrying in the same millisecond.

Caches can help repeated searches, category facets, or product lookups, but they are dangerous when treated as free performance. A cache can hide stale catalog data, create memory pressure, or collapse during key churn. Cache hit ratio, eviction rate, and freshness guarantees matter as much as the latency win.

## Local API Safeguards

The TypeScript API configures an Elasticsearch request timeout and returns a sanitized `503 Service Unavailable` shape when the backend is unavailable. It logs request completion as structured fields and redacts sensitive values from logs. Stack traces and connection details stay server-side.

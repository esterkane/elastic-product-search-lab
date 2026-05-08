---
id: latency-budget
title: Latency Budget For Reranking
topic: performance
---

Reranking can improve answer quality after hybrid retrieval, but it adds latency. Track p95 latency by retrieval stage, cap candidate windows, and fall back to fused results when the reranker is unavailable.

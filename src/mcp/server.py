"""FastMCP server for the elastic-product-search-lab.

Exposes the product-search core as two read-only MCP tools that any MCP client
(Claude Code, Cursor, a LangGraph agent) can call over stdio:

- ``product_search`` — run one of the three comparable BM25 strategies and
  return shaped product hits.
- ``list_strategies`` — list the strategy names with a one-line description.

The tool *logic* lives in :mod:`src.mcp.tools` as plain functions; the wrappers
here supply the cached Elasticsearch client singleton and the configured index.
Both tools are read-only — no ingestion, no index mutation, no writes.

Run it with::

    npm run mcp           # from the repo root
    # or directly:
    .\\.venv\\Scripts\\python.exe -m src.mcp.server
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from scripts.create_index import build_client
from src.mcp.tools import list_strategies_impl, product_search_impl

DEFAULT_INDEX = "products-v1"

mcp = FastMCP("product-search-lab")


@lru_cache(maxsize=1)
def get_es_client() -> Any:
    """Cached read-only Elasticsearch client, built from the same env/.env config
    as the rest of the lab (``scripts/create_index.build_client``)."""

    return build_client()


def get_index() -> str:
    return os.getenv("PRODUCT_INDEX", DEFAULT_INDEX)


@mcp.tool()
def product_search(query: str, strategy: str | None = None, size: int = 10) -> dict[str, Any]:
    """Search the product catalog with one BM25 relevance strategy (read-only).

    WHAT IT DOES: Runs a single product-search strategy against the indexed
    Elasticsearch product catalog and returns the top matching products with
    their relevance score and full normalized fields (productId, title, brand,
    category, price, availability, popularityScore, ...). This is a read-only
    query; it never modifies the index.

    WHEN TO USE: To retrieve products for a natural-language query, or to compare
    how a query ranks under different strategies. Call `list_strategies` first if
    you are unsure which strategy names are valid.

    INPUTS:
      - query (str, required): natural-language search query (non-empty).
      - strategy (str, optional, default "enriched_profile"): one of
        "baseline_bm25" (plain BM25 baseline), "boosted_bm25" (BM25 + popularity
        & recency boosts), "enriched_profile" (BM25 over the enriched
        search_profile field).
      - size (int, default 10, 1..50): maximum number of products to return.

    OUTPUT: {strategy, query, took, total, count, products: [{productId, title,
    description, brand, category, attributes, price, currency, availability,
    popularityScore, sellerId, updatedAt, score}]}. `products` is ordered
    best-first and may be empty when nothing matches.

    EDGE CASES & FAILURES: An empty `products` list with no error means nothing
    matched. On failure a structured error is returned instead:
    errorCategory="validation" (empty query, unknown strategy, size out of
    range) is not retryable; "transient" (search backend unreachable) is
    retryable. Stack traces are never returned.
    """

    return product_search_impl(
        query,
        strategy,
        size=size,
        client=get_es_client(),
        index=get_index(),
    )


@mcp.tool()
def list_strategies() -> dict[str, Any]:
    """List the available product-search strategies (read-only, no backend call).

    WHAT IT DOES: Returns the executable strategy names with a one-line
    description of each, plus which one is the default. No Elasticsearch call is
    made.

    WHEN TO USE: For planning, to discover the valid `strategy` values before
    calling `product_search`.

    INPUTS: none.

    OUTPUT: {count, default, strategies: [{name, description}]}.

    EDGE CASES & FAILURES: This tool does not touch the backend, so it does not
    return transient errors under normal use; on an unexpected internal error a
    structured error is returned. Stack traces are never returned.
    """

    return list_strategies_impl()


def main() -> None:
    """Run the FastMCP server over stdio (for Claude Code / local agents)."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

"""Adapt this lab's search to the shared ``relevance_eval`` skill's ``search_fn``.

The skill's harness (``relevance_eval.run_evaluation``) is backend-agnostic: it
calls an injected ``search_fn(query, strategy) -> Sequence[doc_id]`` and never
talks to Elasticsearch itself. This module is the *only* glue: it wraps the
lab's single source of truth, :func:`src.search.strategies.search_products`,
and extracts the product ids from its shaped response.

It deliberately contains **no business logic and no metric math** — query
building, strategy selection, and result shaping all stay in
``src/search/strategies.py``; the metrics all live in the skill. Elasticsearch
is *not* hard-coded here: the caller injects the client (or a zero-arg factory
that returns one), so the same adapter is used by the runner against a live
cluster and by the unit tests against a fake client.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from src.search.strategies import search_products

# Re-exported for callers/tests that want to assert against the canonical name.
DEFAULT_INDEX = "products-v1"
DEFAULT_SIZE = 10


def make_search_fn(
    es_client_or_factory: Any,
    *,
    index_name: str = DEFAULT_INDEX,
    size: int = DEFAULT_SIZE,
) -> Callable[[str, str], Sequence[str]]:
    """Build the skill's ``search_fn`` from an Elasticsearch client (or factory).

    ``es_client_or_factory`` is either an Elasticsearch client exposing
    ``.search(index=..., **body)`` or a zero-argument callable returning such a
    client (resolved once, lazily, on first search). The returned callable has
    the exact signature the skill expects::

        search(query: str, strategy: str) -> list[str]   # ranked product ids

    The ids are the ``productId`` values from
    :func:`src.search.strategies.search_products`, in ranked (best-first) order.
    """

    resolved: dict[str, Any] = {}

    def _client() -> Any:
        if "client" not in resolved:
            client = es_client_or_factory
            if callable(getattr(client, "search", None)) is False and callable(client):
                client = client()
            resolved["client"] = client
        return resolved["client"]

    def search(query: str, strategy: str) -> list[str]:
        response = search_products(_client(), index_name, query, strategy, size)
        return [str(product["productId"]) for product in response["products"]]

    return search

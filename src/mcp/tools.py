"""MCP tool handlers wrapping the product-search core.

These are plain, importable functions — no FastMCP or HTTP coupling — so they
can be unit-tested directly with a fake Elasticsearch client (no live ES).
``src/mcp/server.py`` registers thin FastMCP wrappers that supply the cached ES
client singleton.

Every handler is wrapped by :func:`src.mcp.errors.guard`, so it either returns a
structured success payload or a structured error payload — never a raised
exception or a stack trace. The handlers add NO business logic: input
validation plus a single call into ``src.search.strategies`` is all they do.
"""

from __future__ import annotations

from typing import Any

from src.mcp.errors import ToolValidationError, guard
from src.search.strategies import (
    DEFAULT_STRATEGY,
    MAX_SIZE,
    STRATEGY_INFOS,
    STRATEGY_NAMES,
    is_strategy,
    search_products,
)


def _validate_query(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ToolValidationError("`query` must be a non-empty string.")
    return query.strip()


def _validate_strategy(strategy: str | None) -> str:
    if strategy is None:
        return DEFAULT_STRATEGY
    if not isinstance(strategy, str) or not is_strategy(strategy):
        raise ToolValidationError(
            f"`strategy` must be one of {list(STRATEGY_NAMES)}.",
            details={"strategy": strategy, "allowed": list(STRATEGY_NAMES)},
        )
    return strategy


def _validate_size(size: int) -> int:
    if not isinstance(size, int) or isinstance(size, bool) or not (1 <= size <= MAX_SIZE):
        raise ToolValidationError(
            f"`size` must be an integer between 1 and {MAX_SIZE}.",
            details={"size": size},
        )
    return size


@guard("product_search")
def product_search_impl(
    query: str,
    strategy: str | None = None,
    *,
    size: int = 10,
    client: Any,
    index: str,
) -> dict[str, Any]:
    """Run one product-search strategy and return shaped results.

    Thin adapter: validate inputs, then call
    :func:`src.search.strategies.search_products`. Returns the same shape the
    HTTP ``/search`` route returns (``products`` is a list of normalized product
    objects, never raw Elasticsearch hits).
    """

    query = _validate_query(query)
    chosen = _validate_strategy(strategy)
    size = _validate_size(size)
    return search_products(client, index, query, chosen, size)


@guard("list_strategies")
def list_strategies_impl() -> dict[str, Any]:
    """Return the executable strategy names with a one-line description each.

    Read directly from the strategy registry — no I/O, no live ES.
    """

    return {
        "count": len(STRATEGY_INFOS),
        "default": DEFAULT_STRATEGY,
        "strategies": [{"name": info.name, "description": info.description} for info in STRATEGY_INFOS],
    }

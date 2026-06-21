"""Read-only MCP server exposing the product-search core as agent tools.

Thin adapters over the existing ``src/search/strategies.py`` functions:
``product_search`` (per strategy) and ``list_strategies``. No business logic
lives in this layer — see ``docs/mcp.md``.
"""

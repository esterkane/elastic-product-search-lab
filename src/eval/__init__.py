"""Glue between this lab's search and the shared ``relevance_eval`` skill.

The :mod:`relevance_eval` skill (a reusable, backend-agnostic relevance
evaluation package, installed via the ``eval`` optional dependency) takes an
*injected* ``search_fn`` with the signature ``(query, strategy) -> [doc_id]``.
This package contains only the thin adaptation from this lab's
:func:`src.search.strategies.search_products` to that signature — no metric
math, no business logic.
"""

from __future__ import annotations

from src.eval.skill_adapter import make_search_fn

__all__ = ["make_search_fn"]

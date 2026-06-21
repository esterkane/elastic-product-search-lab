"""Structured tool errors for the MCP layer.

MCP tools must never leak an internal stack trace or a raw Elasticsearch error
into a result. Every failure is converted to a small, structured payload::

    {
        "isError": True,
        "errorCategory": "validation" | "transient" | "business",
        "isRetryable": bool,
        "message": "<safe, human-readable summary>",
        "details": { ... },   # optional, safe context only
    }

Handlers raise one of the typed errors below for expected failures; the
:func:`guard` decorator wraps every tool handler so that *any* unexpected
exception is logged server-side (with its traceback) and returned as a generic,
trace-free transient error.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Error categories. The product-search lab is read-only and has no auth, so the
# contract is intentionally limited to these three.
VALIDATION = "validation"
TRANSIENT = "transient"
BUSINESS = "business"


class ToolError(Exception):
    """An expected, classified tool failure carrying a category and retryability."""

    category: str = TRANSIENT
    retryable: bool = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ToolValidationError(ToolError):
    """Bad or unsupported input (unknown strategy, empty query). Not retryable."""

    category = VALIDATION
    retryable = False


class ToolBusinessError(ToolError):
    """A valid request that cannot be satisfied as asked. Not retryable."""

    category = BUSINESS
    retryable = False


class ToolTransientError(ToolError):
    """A backend was momentarily unavailable. Safe to retry."""

    category = TRANSIENT
    retryable = True


def error_result(
    category: str,
    message: str,
    *,
    retryable: bool,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the structured error payload returned in place of a result."""

    return {
        "isError": True,
        "errorCategory": category,
        "isRetryable": retryable,
        "message": message,
        "details": details or {},
    }


def _is_es_connection_error(exc: BaseException) -> bool:
    """True for Elasticsearch connectivity/timeout errors, without importing the
    elasticsearch package at module import time (it is a runtime-only dep)."""

    names = {type(exc).__name__ for exc in (exc, *exc.__class__.__mro__)}
    if {"ConnectionError", "ConnectionTimeout", "TransportError"} & names:
        module = type(exc).__module__ or ""
        if module.startswith("elastic"):
            return True
    text = str(exc).lower()
    return "timeout" in text or "timed out" in text or "connection" in text


def guard(name: str) -> Callable[[Callable[..., dict]], Callable[..., dict]]:
    """Wrap a tool handler so no failure ever escapes as a stack trace.

    - :class:`ToolError` subclasses become their structured category payload.
    - Elasticsearch connection/timeout errors become a retryable transient error.
    - Anything else is logged with its traceback and returned as a generic,
      non-retryable transient error with no internal detail.
    """

    def decorator(fn: Callable[..., dict]) -> Callable[..., dict]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            try:
                return fn(*args, **kwargs)
            except ToolError as exc:
                return error_result(exc.category, exc.message, retryable=exc.retryable, details=exc.details)
            except Exception as exc:  # noqa: BLE001 - last-resort guard; traceback goes to logs only
                if _is_es_connection_error(exc):
                    logger.warning("mcp tool %s: search backend unreachable (%s)", name, type(exc).__name__)
                    return error_result(
                        TRANSIENT,
                        "The search backend is currently unreachable. Please retry shortly.",
                        retryable=True,
                        details={"kind": type(exc).__name__},
                    )
                logger.exception("mcp tool %s failed unexpectedly", name)
                return error_result(
                    TRANSIENT,
                    "An unexpected internal error occurred while handling the request.",
                    retryable=False,
                )

        return wrapper

    return decorator

"""
Legacy tracing utilities.

This module provides backward-compatible decorators for tracing.
For new code, prefer using the tracer.instrument() decorator directly.
"""

from parxy_core.tracing.client import tracer


def trace_with_output(name: str = None):
    """Decorator to trace a function and capture its output.

    DEPRECATED: Use tracer.instrument() instead for new code.

    Parameters
    ----------
    name : str, optional
        Span name. Defaults to function name.

    Example
    -------
    >>> @trace_with_output('convert')
    ... def convert_document(doc) -> Document:
    ...     return Document(...)

    For new code, prefer:
    >>> @tracer.instrument('convert', capture_return=True)
    ... def convert_document(doc) -> Document:
    ...     return Document(...)
    """
    return tracer.instrument(
        name,
        capture_args=False,
        capture_return=True,
    )

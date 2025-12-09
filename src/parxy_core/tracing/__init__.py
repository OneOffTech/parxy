"""
Parxy Tracing Module.

Provides a Logfire-inspired API for OpenTelemetry tracing and metrics.

Usage:
    from parxy_core.tracing import tracer

    # Configure once at startup
    tracer.configure(config=my_config)

    # Use decorator for automatic instrumentation
    @tracer.instrument("my_operation")
    def my_function():
        ...

    # Use context manager for manual spans
    with tracer.span("my_span", key="value"):
        ...

    # Log events to current span
    tracer.info("Something happened", detail="value")

    # Record metrics
    tracer.count("operations.completed", driver="pymupdf")
"""

from parxy_core.tracing.client import (
    ParxyTracer,
    get_tracer,
    tracer,
)

__all__ = [
    'ParxyTracer',
    'get_tracer',
    'tracer',
]

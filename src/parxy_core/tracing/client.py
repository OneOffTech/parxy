"""
Parxy Tracer Client.

This module provides a lightweight, decorator-based API for tracing that makes it
easy to instrument code without boilerplate.

Usage:
    from parxy_core.tracing import tracer

    # Decorator - auto-captures args and return value
    @tracer.instrument("parse_document")
    def parse(self, file, level):
        ...

    # Context manager for spans
    with tracer.span("processing block", driver="pymupdf"):
        ...

    # Structured logging
    tracer.info("Document processed", pages=10)

    # Metrics
    tracer.count("documents.processed", driver="pymupdf")
"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Iterator, Optional, TypeVar, ParamSpec

from opentelemetry import trace, metrics
from opentelemetry.trace import Span, Tracer, StatusCode
from opentelemetry.metrics import Meter, Counter, Histogram
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from parxy_core.models.config import ParxyConfig

P = ParamSpec('P')
R = TypeVar('R')


class LoggingSpanExporter(SpanExporter):
    """A span exporter that wraps another exporter and logs when spans are sent."""

    def __init__(
        self,
        wrapped_exporter: SpanExporter,
        endpoint: str,
        logger: logging.Logger | None = None,
    ):
        self._wrapped_exporter = wrapped_exporter
        self._endpoint = endpoint
        self._logger = logger or logging.getLogger('parxy')

    def export(self, spans) -> SpanExportResult:
        if spans:
            span_count = len(spans)
            self._logger.debug(
                f'Sending {span_count} trace{"s" if span_count > 1 else ""} to {self._endpoint}'
            )
        return self._wrapped_exporter.export(spans)

    def shutdown(self):
        return self._wrapped_exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000):
        return self._wrapped_exporter.force_flush(timeout_millis)


def _serialize_value(value: Any, max_length: int = 10000) -> str:
    """Serialize a value for span attributes with size limits."""
    try:
        if hasattr(value, 'model_dump_json'):
            result = value.model_dump_json()
        elif hasattr(value, 'model_dump'):
            result = json.dumps(value.model_dump(), default=str)
        else:
            result = json.dumps(value, default=str)

        if len(result) > max_length:
            return result[:max_length] + '...[truncated]'
        return result
    except Exception:
        return str(value)[:max_length]


def _serialize_args(
    args: tuple,
    kwargs: dict,
    exclude: set[str] | None = None,
    max_length: int = 1000,
) -> dict[str, str]:
    """Serialize function arguments for span attributes."""
    exclude = exclude or {'self', 'cls'}
    attributes = {}

    for i, arg in enumerate(args):
        key = f'arg.{i}'
        if key not in exclude:
            attributes[key] = _serialize_value(arg, max_length)

    for key, value in kwargs.items():
        if key not in exclude:
            attributes[f'arg.{key}'] = _serialize_value(value, max_length)

    return attributes


class ParxyTracer:
    """Parxy tracing client.

    Provides a simple, ergonomic API for tracing with decorators, context managers,
    and structured logging.

    Attributes:
        _tracer: The underlying OpenTelemetry tracer
        _meter: The underlying OpenTelemetry meter
        _logger: Logger for verbose output
        _initialized: Whether the tracer has been configured
        _enabled: Whether tracing is enabled
        _counters: Cache of created counters
        _histograms: Cache of created histograms
    """

    def __init__(self):
        self._tracer: Tracer | None = None
        self._meter: Meter | None = None
        self._logger: logging.Logger = logging.getLogger('parxy')
        self._initialized: bool = False
        self._enabled: bool = False
        self._endpoint: str | None = None
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}

    def configure(
        self,
        config: ParxyConfig | None = None,
        logger: logging.Logger | None = None,
        verbose: bool = False,
    ) -> ParxyTracer:
        """Configure the tracer with the given settings.

        This method should be called once during application startup.
        Subsequent calls are ignored.

        Parameters
        ----------
        config : ParxyConfig, optional
            Configuration containing tracing settings. If None, creates default config.
        logger : logging.Logger, optional
            Logger for trace notifications. Uses 'parxy' logger if not provided.
        verbose : bool, optional
            If True, logs when traces are sent. Default False.

        Returns
        -------
        ParxyTracer
            Self for method chaining.
        """
        if self._initialized:
            return self

        if logger:
            self._logger = logger

        config = config or ParxyConfig()

        # Set up trace provider
        trace_provider = TracerProvider()
        metric_readers = []

        if config.tracing.enable:
            self._enabled = True
            self._endpoint = config.tracing.endpoint

            auth_headers = {}

            if config.tracing.api_key:
                auth_headers = {
                    config.tracing.authentication_header: config.tracing.api_key.get_secret_value()
                }

            # Create OTLP span exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=config.tracing.traces_endpoint,
                headers=auth_headers,
            )

            # Wrap with logging if verbose
            exporter = (
                LoggingSpanExporter(otlp_exporter, self._endpoint, self._logger)
                if verbose
                else otlp_exporter
            )

            trace_provider.add_span_processor(BatchSpanProcessor(exporter))

            # Configure metrics if enabled
            if config.tracing.enable_metrics:
                metric_exporter = OTLPMetricExporter(
                    endpoint=config.tracing.metrics_endpoint,
                    headers=auth_headers,
                )
                metric_reader = PeriodicExportingMetricReader(
                    exporter=metric_exporter,
                    export_interval_millis=60000,
                )
                metric_readers.append(metric_reader)

        # Set up providers
        trace.set_tracer_provider(trace_provider)
        self._tracer = trace.get_tracer('parxy')

        meter_provider = MeterProvider(metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)
        self._meter = metrics.get_meter('parxy')

        self._initialized = True
        return self

    @property
    def is_configured(self) -> bool:
        """Check if the tracer has been configured."""
        return self._initialized

    @property
    def is_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self._enabled

    def _ensure_initialized(self) -> None:
        """Ensure tracer is initialized, using no-op if not configured."""
        if not self._initialized:
            # Lazy init with no-op tracer/meter
            self._tracer = trace.get_tracer('parxy')
            self._meter = metrics.get_meter('parxy')

    # -------------------------------------------------------------------------
    # Decorator API
    # -------------------------------------------------------------------------

    def instrument(
        self,
        name: str | None = None,
        *,
        capture_args: bool = True,
        capture_return: bool = True,
        exclude_args: set[str] | None = None,
        max_arg_length: int = 1000,
        max_return_length: int = 10000,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """Decorator to automatically instrument a function with tracing.

        Creates a span around the function call and optionally captures arguments
        and return values as span attributes.

        Parameters
        ----------
        name : str, optional
            Span name. Defaults to function name.
        capture_args : bool, optional
            Whether to capture function arguments. Default True.
        capture_return : bool, optional
            Whether to capture return value. Default True.
        exclude_args : set[str], optional
            Argument names to exclude from capture. Always excludes 'self', 'cls'.
        max_arg_length : int, optional
            Max length for serialized arguments. Default 1000.
        max_return_length : int, optional
            Max length for serialized return value. Default 10000.

        Returns
        -------
        Callable
            Decorated function.

        Example
        -------
        >>> @tracer.instrument('parse_document')
        ... def parse(self, file: str, level: str = 'block') -> Document:
        ...     return do_parsing(file, level)
        """
        exclude = (exclude_args or set()) | {'self', 'cls'}

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            span_name = name or func.__name__

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                self._ensure_initialized()

                attributes: dict[str, Any] = {'function': func.__qualname__}

                if capture_args:
                    attributes.update(
                        _serialize_args(args, kwargs, exclude, max_arg_length)
                    )

                with self._tracer.start_as_current_span(
                    span_name, attributes=attributes
                ) as span:
                    try:
                        result = func(*args, **kwargs)

                        if capture_return and result is not None:
                            span.set_attribute(
                                'return', _serialize_value(result, max_return_length)
                            )

                        return result

                    except Exception as exc:
                        span.set_status(StatusCode.ERROR, str(exc))
                        span.record_exception(exc)
                        raise

            return wrapper

        return decorator

    # -------------------------------------------------------------------------
    # Context Manager API
    # -------------------------------------------------------------------------

    @contextmanager
    def span(
        self,
        name: str,
        **attributes: Any,
    ) -> Iterator[Span]:
        """Create a tracing span as a context manager.

        Parameters
        ----------
        name : str
            Name of the span.
        **attributes : Any
            Additional attributes to attach to the span. Values are automatically
            serialized to strings.

        Yields
        ------
        Span
            The OpenTelemetry span.

        Example
        -------
        >>> with tracer.span('process_page', page_num=1, driver='pymupdf') as span:
        ...     result = process_page(page)
        ...     span.set_attribute('blocks_found', len(result.blocks))
        """
        self._ensure_initialized()

        # Serialize attribute values
        serialized_attrs = {
            k: _serialize_value(v) if not isinstance(v, (str, int, float, bool)) else v
            for k, v in attributes.items()
        }

        with self._tracer.start_as_current_span(
            name, attributes=serialized_attrs
        ) as span:
            try:
                yield span
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise

    # -------------------------------------------------------------------------
    # Logging API
    # -------------------------------------------------------------------------

    def _log_event(self, level: str, message: str, **attributes: Any) -> None:
        """Add an event to the current span with structured attributes."""
        self._ensure_initialized()

        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            serialized = {
                k: _serialize_value(v)
                if not isinstance(v, (str, int, float, bool))
                else v
                for k, v in attributes.items()
            }
            serialized['level'] = level
            current_span.add_event(message, attributes=serialized)

    def info(self, message: str, **attributes: Any) -> None:
        """Log an info event to the current span.

        Parameters
        ----------
        message : str
            Event message.
        **attributes : Any
            Structured attributes to attach.

        Example
        -------
        >>> tracer.info('Document loaded', pages=10, file_size=1024)
        """
        self._log_event('info', message, **attributes)

    def debug(self, message: str, **attributes: Any) -> None:
        """Log a debug event to the current span."""
        self._log_event('debug', message, **attributes)

    def warn(self, message: str, **attributes: Any) -> None:
        """Log a warning event to the current span."""
        self._log_event('warn', message, **attributes)

    def error(self, message: str, **attributes: Any) -> None:
        """Log an error event to the current span."""
        self._log_event('error', message, **attributes)

    # -------------------------------------------------------------------------
    # Metrics API
    # -------------------------------------------------------------------------

    def _get_counter(self, name: str, description: str = '', unit: str = '') -> Counter:
        """Get or create a counter metric."""
        full_name = f'parxy.{name}'
        if full_name not in self._counters:
            self._ensure_initialized()
            self._counters[full_name] = self._meter.create_counter(
                name=full_name,
                description=description,
                unit=unit,
            )
        return self._counters[full_name]

    def _get_histogram(
        self, name: str, description: str = '', unit: str = ''
    ) -> Histogram:
        """Get or create a histogram metric."""
        full_name = f'parxy.{name}'
        if full_name not in self._histograms:
            self._ensure_initialized()
            self._histograms[full_name] = self._meter.create_histogram(
                name=full_name,
                description=description,
                unit=unit,
            )
        return self._histograms[full_name]

    def count(
        self,
        name: str,
        value: int = 1,
        *,
        description: str = '',
        unit: str = '',
        **labels: str,
    ) -> None:
        """Increment a counter metric.

        Parameters
        ----------
        name : str
            Counter name (will be prefixed with 'parxy.').
        value : int, optional
            Amount to increment. Default 1.
        description : str, optional
            Counter description (used on first creation).
        unit : str, optional
            Unit of measurement.
        **labels : str
            Labels/attributes for the metric.

        Example
        -------
        >>> tracer.count('documents.processed', driver='pymupdf')
        >>> tracer.count('pages.extracted', value=10, driver='llamaparse')
        """
        counter = self._get_counter(name, description, unit)
        counter.add(value, labels)

    def histogram(
        self,
        name: str,
        value: float,
        *,
        description: str = '',
        unit: str = '',
        **labels: str,
    ) -> None:
        """Record a histogram measurement.

        Parameters
        ----------
        name : str
            Histogram name (will be prefixed with 'parxy.').
        value : float
            Value to record.
        description : str, optional
            Histogram description (used on first creation).
        unit : str, optional
            Unit of measurement.
        **labels : str
            Labels/attributes for the metric.

        Example
        -------
        >>> tracer.histogram('parse.duration', 1.5, unit='s', driver='pymupdf')
        >>> tracer.histogram('document.size', 1024, unit='bytes')
        """
        hist = self._get_histogram(name, description, unit)
        hist.record(value, labels)

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_current_span(self) -> Span | None:
        """Get the current active span, if any."""
        span = trace.get_current_span()
        return span if span and span.is_recording() else None

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the current span.

        Parameters
        ----------
        key : str
            Attribute key.
        value : Any
            Attribute value (will be serialized if needed).
        """
        span = self.get_current_span()
        if span:
            serialized = (
                _serialize_value(value)
                if not isinstance(value, (str, int, float, bool))
                else value
            )
            span.set_attribute(key, serialized)


# Global singleton instance
_tracer_instance: ParxyTracer | None = None


def get_tracer() -> ParxyTracer:
    """Get the global ParxyTracer instance.

    Returns
    -------
    ParxyTracer
        The singleton tracer instance.
    """
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = ParxyTracer()
    return _tracer_instance


# Convenience alias for cleaner imports
tracer = get_tracer()

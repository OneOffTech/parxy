from typing import Optional
import logging

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from parxy_core.models.config import ParxyConfig


class LoggingSpanExporter(SpanExporter):
    """A span exporter that wraps another exporter and logs when spans are sent.

    This exporter provides visibility into when traces are being transmitted,
    particularly useful in CLI contexts where users want to know when telemetry
    is sent.
    """

    def __init__(
        self,
        wrapped_exporter: SpanExporter,
        endpoint: str,
        logger: logging.Logger = None,
    ):
        """Initialize the logging span exporter.

        Parameters
        ----------
        wrapped_exporter : SpanExporter
            The actual exporter that sends the spans (e.g., OTLPSpanExporter)
        endpoint : str
            The endpoint URL for display in log messages
        logger : logging.Logger, optional
            Logger instance to use. If None, uses the root logger.
        """
        self._wrapped_exporter = wrapped_exporter
        self._endpoint = endpoint
        self._logger = logger or logging.getLogger('parxy')

    def export(self, spans) -> SpanExportResult:
        """Export spans and log the operation.

        Parameters
        ----------
        spans : Sequence[ReadableSpan]
            The spans to export

        Returns
        -------
        SpanExportResult
            The result of the export operation
        """
        if spans:
            span_count = len(spans)
            self._logger.debug(
                f'Sending {span_count} trace{"s" if span_count > 1 else ""} to {self._endpoint}'
            )

        return self._wrapped_exporter.export(spans)

    def shutdown(self):
        """Shutdown the wrapped exporter."""
        return self._wrapped_exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000):
        """Force flush the wrapped exporter.

        Parameters
        ----------
        timeout_millis : int
            Timeout in milliseconds

        Returns
        -------
        bool
            True if flush succeeded, False otherwise
        """
        return self._wrapped_exporter.force_flush(timeout_millis)


# Global tracer and meter instances
tracer = None
meter = None
documents_processed_counter = None
_initialized = False
_tracing_enabled = False
_tracing_endpoint = None


def initialize_tracing(
    config: ParxyConfig, logger: logging.Logger = None, verbose: bool = False
) -> None:
    """Initialize OpenTelemetry tracing and metrics with the provided configuration.

    This function should be called once during application initialization.

    Parameters
    ----------
    config : ParxyConfig
        The Parxy configuration containing tracing settings
    logger : logging.Logger, optional
        Logger instance to use for trace notifications. If None, uses root logger.
    verbose : bool, optional
        If True, logs when traces are sent (useful for CLI). Default False.
    """
    global \
        tracer, \
        meter, \
        documents_processed_counter, \
        _initialized, \
        _tracing_enabled, \
        _tracing_endpoint

    if _initialized:
        return

    # Initialize tracing
    trace_provider = TracerProvider()
    # Add console exporter
    # processor = BatchSpanProcessor(ConsoleSpanExporter())
    # trace_provider.add_span_processor(processor)

    # Initialize metrics
    metric_readers = []

    # Configure traces if enabled
    if config.tracing.enable:
        _tracing_enabled = True
        _tracing_endpoint = config.tracing.endpoint

        if not config.tracing.api_key:
            raise ValueError(
                'Tracing enabled without API key. Set PARXY_TRACING_API_KEY to submit traces to the observability collector.'
            )

        _authenticationHeaders = {
            config.tracing.authentication_header: config.tracing.api_key.get_secret_value()
        }

        # Create the OTLP span exporter
        otlp_span_exporter = OTLPSpanExporter(
            endpoint=config.tracing.traces_endpoint,
            headers=_authenticationHeaders,
        )

        # Wrap with logging exporter if verbose mode is enabled
        if verbose:
            exporter = LoggingSpanExporter(
                wrapped_exporter=otlp_span_exporter,
                endpoint=config.tracing.endpoint,
                logger=logger,
            )
        else:
            exporter = otlp_span_exporter

        trace_provider.add_span_processor(BatchSpanProcessor(exporter))

        # Configure metrics if enabled
        if config.tracing.enable_metrics:
            # Create the OTLP metric exporter
            otlp_metric_exporter = OTLPMetricExporter(
                endpoint=config.tracing.metrics_endpoint,
                headers=_authenticationHeaders,
            )

            # Add metric reader with periodic export
            metric_reader = PeriodicExportingMetricReader(
                exporter=otlp_metric_exporter,
                export_interval_millis=config.tracing.metrics_export_interval_millis
                if config.tracing.metrics_export_interval_millis != None
                else 60000,
            )
            metric_readers.append(metric_reader)

    # Set up providers
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer('parxy')

    # Set up meter provider with all configured readers
    meter_provider = MeterProvider(metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter('parxy')

    # Create the documents processed counter
    documents_processed_counter = meter.create_counter(
        name='parxy.documents.processed',
        description='Total number of documents processed by each driver',
        unit='documents',
    )

    _initialized = True


def get_tracer():
    """Get the global tracer instance.

    Returns
    -------
    Tracer
        The OpenTelemetry tracer instance
    """
    global tracer
    if tracer is None:
        # Fallback: create a no-op tracer if not initialized
        tracer = trace.get_tracer('parxy')
    return tracer


def get_meter():
    """Get the global meter instance.

    Returns
    -------
    Meter
        The OpenTelemetry meter instance
    """
    global meter
    if meter is None:
        # Fallback: create a no-op meter if not initialized
        meter = metrics.get_meter('parxy')
    return meter


def get_documents_counter():
    """Get the documents processed counter.

    Returns
    -------
    Counter
        The counter for tracking documents processed by each driver
    """
    global documents_processed_counter
    if documents_processed_counter is None:
        # Fallback: create counter if not initialized
        meter = get_meter()
        documents_processed_counter = meter.create_counter(
            name='parxy.documents.processed',
            description='Total number of documents processed by each driver',
            unit='documents',
        )
    return documents_processed_counter

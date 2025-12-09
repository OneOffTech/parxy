# Observability with OpenTelemetry

## Understanding Parxy's Observability

Parxy includes built-in observability capabilities using [OpenTelemetry](https://opentelemetry.io/). This integration enables you to monitor document processing workflows, track performance, identify bottlenecks, and understand how your documents are being processed.

## Why Observability Matters

When processing documents at scale or integrating Parxy into production systems, visibility into the parsing pipeline becomes crucial:

- **Performance Monitoring**: Track how long documents take to process across different drivers
- **Usage Tracking**: Count how many documents are processed by each driver
- **Error Investigation**: Understand where and why parsing failures occur
- **Optimization**: Identify slow operations and optimize your document processing workflow
- **Debugging**: See detailed execution traces for complex multi-step operations

## What is OpenTelemetry?

OpenTelemetry (OTel) is a vendor-neutral standard for collecting telemetry data from applications. It provides:

- **Traces**: Capture the flow of execution through your application, showing which operations occurred and their durations
- **Metrics**: Track numerical measurements over time (counters, gauges, histograms)

Parxy uses OpenTelemetry to export observability data to any compatible backend (Jaeger, Grafana, Honeycomb, DataDog, etc.).

## Observability in Parxy

### Architecture

Parxy's observability system consists of three components:

1. **Instrumentation**: Code-level integration using the `ParxyTracer` client
2. **OpenTelemetry SDK**: Collects and batches telemetry data
3. **OTLP Exporter**: Sends data to an OpenTelemetry Collector or compatible backend

```
┌─────────────┐
│ Parxy Core  │──┐
│  & Drivers  │  │ tracer.instrument()
└─────────────┘  │ tracer.span()
                 │ tracer.count()
                 ▼
         ┌───────────────┐
         │  ParxyTracer  │
         │ (OTel Client) │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │  OTLP         │
         │  Exporter     │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │ OTel Collector│
         │  or Backend   │
         └───────────────┘
```

### Traces

Traces capture the execution flow when parsing documents. Each parsing operation creates a **span** (a named, timed operation) that records:

- Operation name (e.g., "parse_document", "extract_text_blocks")
- Start time and duration
- Input parameters (file path, extraction level, driver name)
- Return values (number of pages, blocks extracted)
- Nested operations (child spans)

#### Trace Hierarchy

When you parse a document, Parxy creates a trace hierarchy like this:

```
parse_document (root span)
├─ driver.handle (PyMuPDFDriver)
│  ├─ extract_pages
│  │  ├─ extract_blocks (page 1)
│  │  ├─ extract_blocks (page 2)
│  │  └─ ...
│  └─ normalize_output
└─ [completion]
```

Each span captures timing information, allowing you to identify which operations are slow.

#### What Gets Traced

Parxy automatically traces:

- **Document parsing**: The entire `parse()` operation from start to finish
- **Driver operations**: Specific driver implementations (PyMuPDF, LlamaParse, etc.)
- **Function calls**: Key internal functions decorated with `@tracer.instrument()`
- **Custom spans**: Manually instrumented operations using context managers

#### Span Attributes

Spans include rich metadata:

- **Function signature**: Name and qualified path of the function
- **Arguments**: Input parameters (file path, level, driver options)
- **Return values**: Structured output (truncated for large objects)
- **Driver context**: Which parser was used
- **Error information**: Exception details when failures occur

### Metrics

In addition to traces, Parxy collects metrics that aggregate data over time.

#### documents.processed

The primary metric is `parxy.documents.processed`, a **counter** that tracks how many documents have been successfully processed. This metric includes a label for the driver name:

```
parxy.documents.processed{driver="PyMuPDFDriver"} = 42
parxy.documents.processed{driver="LlamaParseDriver"} = 15
```

This allows you to:
- Monitor overall processing volume
- Compare usage across different drivers
- Set up alerts for processing thresholds
- Analyze usage patterns over time

#### documents.failures

Additionally, Parxy tracks `parxy.documents.failures`, a **counter** for documents that failed to process due to errors:

```
parxy.documents.failures{driver="PyMuPDFDriver"} = 3
parxy.documents.failures{driver="LlamaParseDriver"} = 1
```

This metric helps you:
- Monitor error rates
- Identify problematic drivers
- Set up alerts for processing failures
- Calculate success/failure ratios

Metrics are exported periodically (every 60 seconds by default) to the configured backend.

### Structured Logging

While not exported via OpenTelemetry, Parxy's tracer client provides structured logging methods that add events to active spans:

- `tracer.info()` - Informational events
- `tracer.warn()` - Warnings
- `tracer.error()` - Errors
- `tracer.debug()` - Debug information

These events appear within trace spans in your observability backend, providing additional context.

## OpenTelemetry Collector

Parxy supports sending telemetry to any [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/), which acts as a vendor-neutral aggregation point. The collector can:

- Receive traces and metrics via OTLP (OpenTelemetry Protocol)
- Process, filter, and transform telemetry data
- Export to multiple backends (Jaeger, Prometheus, Grafana, cloud providers)
- Buffer data to handle backend outages

### Docker Compose Integration

The `parxy docker` command generates a `compose.yaml` file that includes an OpenTelemetry Collector service with a basic configuration. This provides a quick way to start collecting observability data locally.

The included collector configuration (`otel-collector-config.yaml`) exports to the debug exporter by default, which logs telemetry to stdout. This is useful for development and debugging, but you should configure proper exporters for production use.

## Use Cases

### Production Monitoring

Send traces to a dedicated observability backend:

```bash
export PARXY_TRACING_ENABLE=True
export PARXY_TRACING_ENDPOINT=https://otel-collector.example.com:4318/
export PARXY_TRACING_ENABLE_METRICS=True
export PARXY_TRACING_API_KEY=your-api-key
```

This allows your operations team to monitor document processing health and performance.

### Performance Analysis

Use trace data to identify bottlenecks:
1. Parse a representative set of documents
2. Examine span durations in your observability tool
3. Find the slowest operations
4. Optimize or parallelize those operations

### Driver Comparison

Compare the performance of different drivers on similar documents:
1. Enable metrics collection
2. Process documents with multiple drivers
3. Query `parxy.documents.processed` metric by driver label
4. Compare processing times from trace spans

## Privacy and Security Considerations

### Data in Traces

Traces may contain sensitive information:
- File paths and names
- Document metadata
- Processing parameters

Parxy attempts to limit trace data, but you should:
- Review what data is being exported
- Configure your collector to filter sensitive attributes
- Use secure transport (HTTPS) for OTLP endpoints
- Restrict access to your observability backend

### Authentication

When sending traces to authenticated backends:
- Use environment variables for API keys
- Leverage the `PARXY_TRACING_API_KEY` configuration
- Customize `PARXY_TRACING_AUTHENTICATION_HEADER` if needed

### Disabling Observability

Observability is **opt-in** and disabled by default. To completely disable:

- Set `PARXY_TRACING_ENABLE=False` (or omit configuration)

## Further Reading

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Distributed Tracing concepts](https://opentelemetry.io/docs/concepts/observability-primer/#distributed-traces)

For practical configuration steps, see [How to Configure Observability](../howto/configure_observability.md).

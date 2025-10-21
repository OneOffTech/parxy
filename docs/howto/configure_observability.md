# How to Configure Observability

This guide shows you how to enable and configure OpenTelemetry-based observability in Parxy to monitor document processing operations.

## Prerequisites

- Parxy installed (`pip install parxy`)
- An OpenTelemetry Collector or compatible observability backend (optional for local development)

## Quick Start: Local Development

The fastest way to get started with observability is using the built-in Docker Compose setup.

### Step 1: Generate Docker Compose File

Run the `parxy docker` command to create a `compose.yaml` file with pre-configured services:

```bash
parxy docker
```

This creates:
- `compose.yaml` - Docker Compose configuration with PDFAct and OpenTelemetry Collector
- `otel-collector-config.yaml` - Example collector configuration (you need to create this separately)

### Step 2: Create OpenTelemetry Collector Configuration

Create an `otel-collector-config.yaml` file in your project directory:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:

exporters:
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
```

This basic configuration:
- Accepts OTLP data on ports 4317 (gRPC) and 4318 (HTTP)
- Batches telemetry data for efficiency
- Exports traces and metrics to console (debug exporter)

### Step 3: Uncomment OpenTelemetry Service

Edit the generated `compose.yaml` and uncomment the `otel-collector` service:

```yaml
services:
  pdfact:
    image: "ghcr.io/data-house/pdfact:main"
    ports:
      - "4567:4567"
    networks:
      - parxy

  # Uncomment this section:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.141.0
    volumes:
      - ./otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml
    ports:
      - 4317:4317 # OTLP gRPC receiver
      - 4318:4318 # OTLP http receiver
    networks:
      - parxy
    command: ["--config=/etc/otelcol-contrib/config.yaml"]

networks:
  parxy:
    driver: bridge
```

### Step 4: Start Services

```bash
docker compose pull
docker compose up -d
```

Verify the collector is running:

```bash
docker compose ps
docker compose logs otel-collector
```

### Step 5: Enable Tracing in Parxy

Create a `.env` file in your project directory:

```bash
# Enable tracing
PARXY_TRACING_ENABLE=True

# Enable metrics (optional)
PARXY_TRACING_ENABLE_METRICS=True

# Collector endpoint (default: http://localhost:4318/)
PARXY_TRACING_ENDPOINT=http://localhost:4318/

# Show trace sends in console
PARXY_TRACING_VERBOSE=True
```

### Step 6: Parse Documents

Now run your Parxy code:

```python
from parxy_core.facade.parxy import Parxy

# Traces will automatically be sent to the collector
doc = Parxy.parse("document.pdf")
print(f"Processed {len(doc.pages)} pages")
```

Check the collector logs to see traces:

```bash
docker compose logs -f otel-collector
```

You should see detailed trace and metric data in the output.

## Configuration Options

### Environment Variables

All observability configuration uses environment variables with the `PARXY_TRACING_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_TRACING_ENABLE` | bool | `False` | Enable sending traces to observability backend |
| `PARXY_TRACING_ENABLE_METRICS` | bool | `False` | Enable sending metrics (requires `ENABLE=True`) |
| `PARXY_TRACING_ENDPOINT` | string | `http://localhost:4318/` | Base URL of OpenTelemetry Collector |
| `PARXY_TRACING_TRACES_ENDPOINT` | string | `{ENDPOINT}/v1/traces` | Specific endpoint for traces (auto-derived) |
| `PARXY_TRACING_METRICS_ENDPOINT` | string | `{ENDPOINT}/v1/metrics` | Specific endpoint for metrics (auto-derived) |
| `PARXY_TRACING_API_KEY` | string | None | API key for authentication |
| `PARXY_TRACING_AUTHENTICATION_HEADER` | string | `Authorization` | HTTP header name for API key |
| `PARXY_TRACING_VERBOSE` | bool | `True` | Log when traces are sent (useful for CLI) |

### Programmatic Configuration

You can also configure observability in code:

```python
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import ParxyConfig

# Create custom configuration
config = ParxyConfig()
config.tracing.enable = True
config.tracing.enable_metrics = True
config.tracing.endpoint = "http://localhost:4318/"
config.tracing.verbose = True

# Parse with custom config
doc = Parxy.parse("document.pdf")
```

The tracer is configured automatically when you first use Parxy. To manually configure it:

```python
from parxy_core.tracing import tracer
from parxy_core.models.config import ParxyConfig

config = ParxyConfig()
config.tracing.enable = True

# Configure tracer explicitly
tracer.configure(config=config, verbose=True)
```

## Understanding Collected Data

### Traces

When you parse a document, Parxy creates trace spans for:

- **Root span**: `parse_document` - The entire parsing operation
- **Driver span**: Specific driver implementation (e.g., `PyMuPDFDriver.handle`)
- **Operation spans**: Internal operations like page extraction, block detection

Each span includes:
- Duration
- Input arguments (file path, level)
- Return values (pages, blocks)
- Error information (if any)

### Metrics

Parxy tracks the following metrics:

#### parxy.documents.processed

Counter tracking successfully processed documents.

Labels:
- `driver`: Name of the driver used (e.g., "PyMuPDFDriver")

Example queries:
- Total documents: `sum(parxy_documents_processed)`
- By driver: `sum(parxy_documents_processed) by (driver)`
- Rate: `rate(parxy_documents_processed[5m])`

#### parxy.documents.failures

Counter tracking documents that failed to process.

Labels:
- `driver`: Name of the driver used (e.g., "PyMuPDFDriver")

Example queries:
- Total failures: `sum(parxy_documents_failures)`
- By driver: `sum(parxy_documents_failures) by (driver)`
- Error rate: `rate(parxy_documents_failures[5m]) / rate(parxy_documents_processed[5m])`
- Success rate: `(sum(parxy_documents_processed) / (sum(parxy_documents_processed) + sum(parxy_documents_failures))) * 100`

Metrics are exported every 60 seconds to the configured endpoint.

## Troubleshooting

### Traces Not Appearing

1. Verify tracing is enabled:
```bash
echo $PARXY_TRACING_ENABLE
```

2. Check collector is reachable:
```bash
curl http://localhost:4318/v1/traces
```

3. Enable verbose mode to see when traces are sent:
```bash
export PARXY_TRACING_VERBOSE=True
```

4. Check collector logs:
```bash
docker compose logs otel-collector
```

### Authentication Errors

If you see 401/403 errors:

1. Verify your API key is correct
2. Check the authentication header name matches your backend's requirements
3. Ensure the API key is properly formatted (some backends require `Bearer` prefix)

Example for Bearer token:
```bash
export PARXY_TRACING_API_KEY="Bearer your-token-here"
```

### Performance Impact

If tracing impacts performance:

1. Reduce captured data size:
```python
# Disable return value capture for large documents
@tracer.instrument("operation", capture_return=False)
def process_large_doc():
    ...
```

2. Disable metrics if only traces are needed:
```bash
export PARXY_TRACING_ENABLE_METRICS=False
```

3. Increase collector batch size to reduce network calls

### Collector Not Starting

If the OpenTelemetry Collector fails to start:

1. Verify configuration syntax:
```bash
docker compose config
```

2. Check collector logs:
```bash
docker compose logs otel-collector
```

3. Validate your `otel-collector-config.yaml`:
```bash
docker run --rm -v $(pwd)/otel-collector-config.yaml:/config.yaml \
  otel/opentelemetry-collector-contrib:0.141.0 \
  validate --config=/config.yaml
```

## Advanced Configuration

### Custom Spans

Add custom instrumentation to your code:

```python
from parxy_core.tracing import tracer

# Using decorator
@tracer.instrument("process_batch")
def process_documents(files):
    for file in files:
        doc = Parxy.parse(file)
        # ...

# Using context manager
with tracer.span("custom_operation", file_count=len(files)) as span:
    result = do_work(files)
    span.set_attribute("documents_processed", len(result))
```

### Filtering Sensitive Data

Configure the collector to filter sensitive attributes:

```yaml
processors:
  attributes:
    actions:
      - key: arg.file_path
        action: delete
      - key: return
        action: delete

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [debug]
```

### Multiple Exporters

Send data to multiple backends:

```yaml
exporters:
  debug:
    verbosity: detailed
  otlp/grafana:
    endpoint: https://otlp-gateway.grafana.net:443
  otlp/honeycomb:
    endpoint: https://api.honeycomb.io:443

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug, otlp/grafana, otlp/honeycomb]
```

## Next Steps

- Read [Observability with OpenTelemetry](../explanation/observability.md) for conceptual understanding
- Explore your traces in your observability backend's UI
- Set up dashboards to visualize document processing metrics
- Configure alerts for processing failures or performance degradation
- Integrate Parxy observability with your existing monitoring infrastructure

## See Also

- [OpenTelemetry Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [OTLP Exporter Configuration](https://opentelemetry.io/docs/specs/otlp/)
- [Parxy Tracing Client API](../../src/parxy_core/tracing/client.py)

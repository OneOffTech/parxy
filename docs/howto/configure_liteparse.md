---
title: Configure LiteParse
description: How to set up the LiteParse driver against a self-hosted LiteParse instance, configure OCR, DPI, and page selection, and override options on a per-document basis.
---

# Configure LiteParse

This guide shows you how to configure the [LiteParse](https://www.llamaindex.ai/blog/liteparse-local-document-parsing-for-ai-agents) driver for document processing using a self-hosted [LiteParse](https://github.com/run-llama/liteparse-server) instance.


## Quick Start

### Step 1: Start LiteParse

Parxy comes with a sample Docker Compose file that includes LiteParse. Generate it in your current directory with:

```bash
parxy docker
```

Then pull the image and start the service:

```bash
docker compose pull liteparse && docker compose up -d liteparse
```

### Step 2: Parse a Document

```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf", driver_name="liteparse")
print(f"Processed {len(doc.pages)} pages")
```

No `.env` configuration is required when LiteParse is running on the default address (`http://localhost:5000`).

## Configuration Options

### Environment Variables

All LiteParse configuration uses environment variables with the `PARXY_LITEPARSE_` prefix:

#### Connection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LITEPARSE_BASE_URL` | string | `http://localhost:5000` | Base URL of the LiteParse server |
| `PARXY_LITEPARSE_TIMEOUT` | float | `30.0` | HTTP request timeout in seconds |

#### OCR

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LITEPARSE_OCR_ENABLED` | bool | `true` | Enable OCR on pages that contain no embedded text |
| `PARXY_LITEPARSE_OCR_LANGUAGE` | string | `en` | Language code for OCR (e.g. `en`, `de`, `fr`) |
| `PARXY_LITEPARSE_OCR_SERVER_URL` | string | None | URL of an external HTTP OCR service; when set, LiteParse delegates OCR over HTTP instead of using in-process Tesseract |
| `PARXY_LITEPARSE_NUM_WORKERS` | int | `4` | Number of pages to OCR in parallel |

#### Processing

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LITEPARSE_MAX_PAGES` | int | None | Maximum number of pages to process (all pages when unset) |
| `PARXY_LITEPARSE_DPI` | int | `150` | DPI used when rasterising pages for OCR |

#### Features

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LITEPARSE_PRECISE_BOUNDING_BOX` | bool | `true` | Use precise bounding-box calculation |
| `PARXY_LITEPARSE_PRESERVE_VERY_SMALL_TEXT` | bool | `false` | Include very small text that would normally be filtered out |
| `PARXY_LITEPARSE_PRESERVE_LAYOUT_ALIGNMENT_ACROSS_PAGES` | bool | `false` | Preserve cross-page layout alignment |

### Example `.env` file

```bash
PARXY_LITEPARSE_BASE_URL=http://liteparse-server:5000
PARXY_LITEPARSE_TIMEOUT=60
PARXY_LITEPARSE_OCR_LANGUAGE=de
PARXY_LITEPARSE_DPI=200
```

## Supported Extraction Levels

| Level | Description |
|-------|-------------|
| `page` | Page-level text only — all text items concatenated per page |
| `block` | Page + individual `TextBlock` items with bounding boxes and font metadata, one per text item returned by LiteParse |

```python
# Page-level extraction (default)
doc = Parxy.parse("document.pdf", driver_name="liteparse", level="page")

# Block-level extraction
doc = Parxy.parse("document.pdf", driver_name="liteparse", level="block")
```

## Bounding Boxes and Style

At `block` level each `TextBlock` includes the exact position and font information reported by LiteParse:

```python
doc = Parxy.parse("document.pdf", driver_name="liteparse", level="block")

for page in doc.pages:
    print(f"Page {page.number}: {page.width} x {page.height}")
    if page.blocks:
        for block in page.blocks:
            if block.bbox:
                print(
                    f"  [{block.bbox.x0:.1f}, {block.bbox.y0:.1f}] "
                    f"→ [{block.bbox.x1:.1f}, {block.bbox.y1:.1f}]  '{block.text}'"
                )
            if block.style:
                print(f"    font: {block.style.font_name}, size: {block.style.font_size}")
```

Each page also exposes `source_data` with the raw LiteParse response for that page (including the full `textItems` array), which is useful when you need fields not mapped to the Parxy model:

```python
for page in doc.pages:
    raw = page.source_data  # original LiteParse page JSON
    if raw:
        for item in raw.get("textItems", []):
            print(item["confidence"])  # OCR confidence score (0–1)
```

## Input Types

### Local Files

```python
doc = Parxy.parse("/path/to/document.pdf", driver_name="liteparse")
```

### Bytes / BytesIO

```python
import io

with open("document.pdf", "rb") as f:
    data = io.BytesIO(f.read())

doc = Parxy.parse(data, driver_name="liteparse")
```

## Per-Call Configuration Overrides

Any `LiteParseConfig` field can be overridden for a single call by passing it as a keyword argument to `Parxy.parse()`.

```python
from parxy_core.facade.parxy import Parxy

# Default configuration
doc1 = Parxy.parse("report.pdf", driver_name="liteparse")

# Higher DPI for a document with small text
doc2 = Parxy.parse(
    "small-text-report.pdf",
    driver_name="liteparse",
    dpi=300,
)

# German OCR for a specific document
doc3 = Parxy.parse(
    "german-contract.pdf",
    driver_name="liteparse",
    ocr_language="de",
)

# Extract only the first three pages
doc4 = Parxy.parse(
    "large-report.pdf",
    driver_name="liteparse",
    target_pages="1,2,3",
)

# Open a password-protected PDF
doc5 = Parxy.parse(
    "protected.pdf",
    driver_name="liteparse",
    password="s3cr3t",
)
```

### Supported Per-Call Options

All `LiteParseConfig` fields (see [environment variables](#environment-variables) above) can be passed as snake_case keyword arguments. In addition:

| Option | Type | Description |
|--------|------|-------------|
| `target_pages` | string | Comma-separated 1-based page numbers to extract (e.g. `"1,3,5"`). Useful for sampling or previewing large documents without processing all pages |
| `password` | string | Password for encrypted PDF documents |

## Use Cases

### Scanned Documents

LiteParse uses Tesseract OCR by default for pages without embedded text. Use `block` level to also get per-word bounding boxes and OCR confidence scores:

```python
doc = Parxy.parse(
    "scanned-invoice.pdf",
    driver_name="liteparse",
    level="block",
    ocr_enabled=True,
    dpi=300,  # higher DPI improves OCR accuracy on small text
)

for page in doc.pages:
    if page.blocks:
        for block in page.blocks:
            raw_item = next(
                (i for i in (page.source_data or {}).get("textItems", []) if i.get("str") == block.text),
                None,
            )
            confidence = raw_item["confidence"] if raw_item else None
            print(f"{block.text!r}  confidence={confidence}")
```

### Non-English Documents

Set `ocr_language` to the primary language of the document for better OCR accuracy:

```python
doc = Parxy.parse(
    "french-report.pdf",
    driver_name="liteparse",
    ocr_language="fr",
)
```

### Sampling Large Documents

Process only a subset of pages to preview content or reduce processing time:

```python
# Preview first and last pages of a 100-page document
doc = Parxy.parse(
    "large-document.pdf",
    driver_name="liteparse",
    target_pages="1,2,99,100",
)
```

### Password-Protected PDFs

```python
doc = Parxy.parse(
    "confidential.pdf",
    driver_name="liteparse",
    password="document-password",
)
```

### Using an External OCR Service

When `ocr_server_url` is set, LiteParse delegates OCR via HTTP instead of running Tesseract in-process. This is useful when OCR is handled by a dedicated service:

```bash
PARXY_LITEPARSE_OCR_SERVER_URL=http://ocr-service:8080
```

## Troubleshooting

### Connection Errors

If you see `Could not connect to LiteParse service`:

1. Verify LiteParse is running: `curl http://localhost:5000`
2. Check that `PARXY_LITEPARSE_BASE_URL` matches the actual address
3. Ensure no firewall or network policy blocks port 5000

### Timeout Errors

For large documents or slow hardware, increase the default timeout:

```bash
PARXY_LITEPARSE_TIMEOUT=120
```

Or per-call:

```python
from parxy_core.models.config import LiteParseConfig
from parxy_core.drivers import LiteParseDriver

driver = LiteParseDriver(config=LiteParseConfig(timeout=120))
doc = driver.parse("large-document.pdf")
```

### Invalid Base URL

The driver validates the base URL on startup:

```python
# Raises ValueError: Invalid base URL
from parxy_core.models.config import LiteParseConfig
from parxy_core.drivers import LiteParseDriver

LiteParseDriver(config=LiteParseConfig(base_url="not-a-url"))
```

### Poor OCR Quality

If extracted text looks garbled:

1. Increase DPI (`dpi=300`) for documents with small or dense text
2. Set the correct `ocr_language` for the document's language
3. Enable `preserve_very_small_text=True` if small annotations are missing

## See Also

- [LiteParse documentation](https://developers.llamaindex.ai/liteparse/)
- [LiteParse Server Repository](https://github.com/run-llama/liteparse-server)
- [Getting Started Tutorial](../tutorials/getting_started.md)

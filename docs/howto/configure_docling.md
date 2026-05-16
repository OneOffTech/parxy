---
title: Configure Docling
description: How to set up the Docling driver against a self-hosted or remote docling-serve instance, configure OCR, PDF backend and table extraction, and override options on a per-document basis.
---

# How to Configure Docling

This guide shows you how to configure the Docling driver for document processing using a running [docling-serve](https://github.com/docling-project/docling-serve) instance.

## Prerequisites

- Parxy installed with Docling support: `pip install parxy[docling]` or via UV `uv add parxy[docling]`
- A running docling-serve instance (see [Self-Hosting Docling Serve](#self-hosting-docling-serve) below)

## Quick Start

### Step 1: Start docling-serve

The simplest way to run docling-serve is with Docker:

```bash
docker run -p 5001:5001 ghcr.io/docling-project/docling-serve-cu128:v1.18.0
```

### Step 2: Parse a Document

```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf", driver_name="docling")
print(f"Processed {len(doc.pages)} pages")
```

No `.env` configuration is required when docling-serve is running on the default address (`http://localhost:5001`).

## Configuration Options

### Environment Variables

All Docling configuration uses environment variables with the `PARXY_DOCLING_` prefix:

#### Connection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_DOCLING_BASE_URL` | string | `http://localhost:5001` | Base URL of the docling-serve instance |
| `PARXY_DOCLING_API_KEY` | string | None | API key for authenticated docling-serve instances |
| `PARXY_DOCLING_TIMEOUT` | float | `120.0` | HTTP request timeout in seconds |

#### Extraction

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_DOCLING_DO_OCR` | bool | `false` | Enable OCR on bitmap content (slower but handles scanned PDFs) |
| `PARXY_DOCLING_DO_TABLE_STRUCTURE` | bool | `true` | Extract table structure |
| `PARXY_DOCLING_PDF_BACKEND` | string | `dlparse_v2` | PDF backend: `dlparse_v2`, `pypdfium2`, `dlparse_v1`, `dlparse_v4` |
| `PARXY_DOCLING_TABLE_MODE` | string | `accurate` | Table extraction mode: `fast` or `accurate` |
| `PARXY_DOCLING_INCLUDE_IMAGES` | bool | `false` | Include images in output |
| `PARXY_DOCLING_IMAGES_SCALE` | float | None | Scale factor for images (server default: 2.0) |
| `PARXY_DOCLING_DO_PICTURE_CLASSIFICATION` | bool | `false` | Classify pictures in documents |
| `PARXY_DOCLING_DO_PICTURE_DESCRIPTION` | bool | `false` | Generate descriptions for pictures (requires a VLM configured on the server) |

### Example `.env` file

```bash
PARXY_DOCLING_BASE_URL=http://docling-server:5001
PARXY_DOCLING_API_KEY=your-secret-key
PARXY_DOCLING_DO_OCR=false
PARXY_DOCLING_PDF_BACKEND=dlparse_v2
PARXY_DOCLING_TABLE_MODE=accurate
PARXY_DOCLING_INCLUDE_IMAGES=false
```

## Supported Extraction Levels

| Level | Description |
|-------|-------------|
| `page` | Page-level text only — text items are concatenated per page |
| `block` | Page + individual blocks (`TextBlock`, `TableBlock`, `ImageBlock`) with bounding boxes |

```python
# Page-level extraction (default)
doc = Parxy.parse("document.pdf", driver_name="docling", level="page")

# Block-level extraction
doc = Parxy.parse("document.pdf", driver_name="docling", level="block")
```

## Input Types

The Docling driver accepts all standard Parxy input types.

### Local Files

The file is read and sent to docling-serve as a base64-encoded payload:

```python
doc = Parxy.parse("/path/to/document.pdf", driver_name="docling")
```

### URLs

The URL is passed directly to docling-serve, which downloads the document server-side:

```python
doc = Parxy.parse("https://arxiv.org/pdf/2206.01062", driver_name="docling")
```

### BytesIO / bytes

Binary content is base64-encoded and sent as a file payload:

```python
import io

with open("document.pdf", "rb") as f:
    data = io.BytesIO(f.read())

doc = Parxy.parse(data, driver_name="docling")
```

## Per-Call Configuration Overrides

You can override any extraction option for a specific document by passing kwargs to `Parxy.parse()`. This is useful when most documents use the default configuration but some need different settings.

```python
from parxy_core.facade.parxy import Parxy

# Default configuration
doc1 = Parxy.parse("digital-pdf.pdf", driver_name="docling")

# Enable OCR for a scanned document
doc2 = Parxy.parse(
    "scanned-invoice.pdf",
    driver_name="docling",
    do_ocr=True,
)

# Faster table extraction for a document with simple tables
doc3 = Parxy.parse(
    "report.pdf",
    driver_name="docling",
    table_mode="fast",
)

# Include images in the output
doc4 = Parxy.parse(
    "illustrated-manual.pdf",
    driver_name="docling",
    level="block",
    include_images=True,
)
```

### Supported Per-Call Options

| Option | Type | Description |
|--------|------|-------------|
| `do_ocr` | bool | Enable OCR on bitmap content |
| `pdf_backend` | string | PDF backend (`dlparse_v2`, `pypdfium2`, `dlparse_v1`, `dlparse_v4`) |
| `table_mode` | string | Table extraction mode (`fast` or `accurate`) |
| `include_images` | bool | Include images in output |
| `images_scale` | float | Scale factor for extracted images |
| `do_picture_classification` | bool | Classify pictures in documents |
| `do_picture_description` | bool | Generate descriptions for pictures |

## Document Structure Roles

Docling labels each extracted element with a semantic category. Parxy maps these to WAI-ARIA document structure roles:

| Docling Label | WAI-ARIA Role | Description |
|---------------|---------------|-------------|
| `title` | `doc-title` | Document title |
| `section_header` | `heading` | Section headings |
| `paragraph` | `paragraph` | Main body text |
| `list_item` | `list` | List items |
| `code` | `generic` | Code blocks |
| `formula` | `generic` | Mathematical formulas |
| `caption` | `generic` | Figure and table captions |
| `footnote` | `doc-footnote` | Footnotes |
| `page_header` | `doc-pageheader` | Page headers |
| `page_footer` | `doc-pagefooter` | Page footers |
| `table` | `table` | Tables |
| `picture` | `figure` | Images and figures |
| `chart` | `figure` | Charts |

Access roles in your code:

```python
doc = Parxy.parse("document.pdf", driver_name="docling", level="block")

for page in doc.pages:
    for block in page.blocks:
        print(f"Role: {block.role}, Category: {block.category}")
        if block.role == "heading":
            print(f"  Heading level: {block.level}")
```

## Bounding Boxes

Each block includes bounding box coordinates derived from the Docling JSON output:

```python
doc = Parxy.parse("document.pdf", driver_name="docling", level="block")

for page in doc.pages:
    print(f"Page {page.number} dimensions: {page.width} x {page.height}")
    if page.blocks:
        for block in page.blocks:
            if block.bbox:
                print(f"  Block at ({block.bbox.x0:.1f}, {block.bbox.y0:.1f}) "
                      f"to ({block.bbox.x1:.1f}, {block.bbox.y1:.1f})")
```

## Use Cases

### Scanned Documents

For documents that are image-based (scanned pages with no embedded text), enable OCR:

```python
doc = Parxy.parse(
    "scanned-contract.pdf",
    driver_name="docling",
    do_ocr=True,
)
```

> **Note**: OCR is significantly slower and more resource-intensive than text extraction. Enable it only when the document is actually scanned.

### Documents with Complex Tables

Docling's `accurate` table mode uses TableFormer, a deep learning model for precise table structure extraction:

```python
doc = Parxy.parse(
    "financial-report.pdf",
    driver_name="docling",
    level="block",
    table_mode="accurate",  # default — use "fast" for simple tables
)

# Tables are extracted as TableBlock with markdown text
for page in doc.pages:
    if page.blocks:
        for block in page.blocks:
            if block.role == "table":
                print(block.text)  # Markdown table format
```

### Illustrated Documents

To include images alongside text in the extracted output:

```python
doc = Parxy.parse(
    "illustrated-guide.pdf",
    driver_name="docling",
    level="block",
    include_images=True,
)

from parxy_core.models import ImageBlock

for page in doc.pages:
    if page.blocks:
        for block in page.blocks:
            if isinstance(block, ImageBlock):
                print(f"Image on page {page.number}: {block.alt_text}")
```

### Processing Remote PDFs

For URLs, docling-serve fetches the document directly, avoiding a round-trip through Parxy:

```python
doc = Parxy.parse(
    "https://arxiv.org/pdf/2206.01062",
    driver_name="docling",
)
```

### Filtering by Block Role

Extract only main body text, skipping headers and footers:

```python
doc = Parxy.parse("document.pdf", driver_name="docling", level="block")

skip_roles = {"doc-pageheader", "doc-pagefooter", "doc-footnote"}
body_blocks = [
    block
    for page in doc.pages
    if page.blocks
    for block in page.blocks
    if block.role not in skip_roles
]
```



## Self-Hosting Docling Serve

### Docker

```bash
# Quick start — CPU only
docker run -p 5001:5001 ghcr.io/docling-project/docling-serve-cu128:v1.18.0

# With GPU support (CUDA)
docker run --gpus all -p 5001:5001 ghcr.io/docling-project/docling-serve-cu128:v1.18.0

# With resource limits
docker run -p 5001:5001 \
    --memory="8g" \
    --cpus="4" \
    ghcr.io/docling-project/docling-serve-cu128:v1.18.0
```

### Docker Compose

```yaml
services:
  docling-serve:
    image: ghcr.io/docling-project/docling-serve-cu128:v1.18.0
    ports:
      - "5001:5001"
    environment:
      - DOCLING_SERVE_API_KEY=your-secret-key  # optional
    restart: unless-stopped
```

Then configure Parxy to use the API key:

```bash
PARXY_DOCLING_API_KEY=your-secret-key
```

### Verify the Service is Running

```bash
curl http://localhost:5001/health
```

Or from Python:

```python
import httpx

response = httpx.get("http://localhost:5001/health")
print(response.json())
```

## Troubleshooting

### Connection Errors

If you see `Cannot connect to Docling server`:

1. Verify docling-serve is running: `curl http://localhost:5001/health`
2. Check the `PARXY_DOCLING_BASE_URL` value matches the actual address
3. Ensure no firewall or network policy blocks the port

### Authentication Errors

If you see `AuthenticationException`:

1. Verify `PARXY_DOCLING_API_KEY` matches the key set in `DOCLING_SERVE_API_KEY` on the server
2. Ensure the key is set in your `.env` file or environment before starting your application

### Timeout Errors

For large documents or slow hardware, the default 120-second timeout may not be enough:

```bash
PARXY_DOCLING_TIMEOUT=300
```

Or per-call (not a per-call override — set it at config level):

```python
config = DoclingConfig(timeout=300.0)
driver = Parxy.driver("docling", config=config)
```

### Poor OCR Results

If OCR output is inaccurate:

1. Ensure the document is genuinely scanned (not a digital PDF) — enabling OCR on digital PDFs is unnecessary and slower
2. Try a higher `images_scale` value so OCR has more pixels to work with:

```python
doc = Parxy.parse("scanned.pdf", driver_name="docling", do_ocr=True, images_scale=3.0)
```

### Missing Tables

If tables are not extracted or have incorrect structure:

1. Ensure `table_mode="accurate"` (the default) is used — `fast` mode skips the deep learning model
2. Verify `PARXY_DOCLING_DO_TABLE_STRUCTURE=true` is set (default)

## See Also

- [docling-serve GitHub Repository](https://github.com/docling-project/docling-serve)
- [Docling Project](https://github.com/docling-project/docling)
- [Document Structure Roles](../explanation/document-roles.md)
- [Getting Started Tutorial](../tutorials/getting_started.md)

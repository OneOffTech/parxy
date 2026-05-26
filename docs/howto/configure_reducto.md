---
title: Configure Reducto
description: How to set up the Reducto driver, configure API key and environment, control extraction mode and table output format, and override options on a per-document basis.
---

# How to Configure Reducto

This guide shows you how to configure the Reducto driver for document processing using the [Reducto Parse API](https://reducto.ai/).

## Prerequisites

- Parxy installed with Reducto support: `pip install parxy[reducto]` or via UV `uv add parxy[reducto]`
- A Reducto API key from [Reducto](https://app.reducto.ai/)

## Quick Start

### Step 1: Set Your API Key

Create a `.env` file in your project directory:

```bash
PARXY_REDUCTO_API_KEY=your-api-key-here
```

Or set it as an environment variable:

```bash
export PARXY_REDUCTO_API_KEY=your-api-key-here
```

### Step 2: Parse a Document

Via the command line

```bash
parxy parse -d reducto document.pdf
```

or via code


```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf", driver_name="reducto")
print(f"Processed {len(doc.pages)} pages")
```

## Configuration Options

### Environment Variables

All Reducto configuration uses environment variables with the `PARXY_REDUCTO_` prefix:

#### Connection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_REDUCTO_API_KEY` | string | None | Your Reducto API key |
| `PARXY_REDUCTO_ENVIRONMENT` | string | None | API environment: `production`, `eu`, `au`. Default uses `production` |
| `PARXY_REDUCTO_BASE_URL` | string | None | Custom base URL. Takes precedence over `environment` when set |
| `PARXY_REDUCTO_TIMEOUT` | float | None | HTTP request timeout in seconds. Default uses the SDK default |

#### Extraction

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_REDUCTO_EXTRACTION_MODE` | string | None | Text extraction mode: `hybrid` (default) or `ocr` |
| `PARXY_REDUCTO_TABLE_OUTPUT_FORMAT` | string | None | Table format: `html`, `json`, `md`, `jsonbbox`, `dynamic`, `csv`. Default uses the API default (`dynamic`) |

### Example `.env` file

```bash
PARXY_REDUCTO_API_KEY=your-api-key-here
PARXY_REDUCTO_ENVIRONMENT=eu
PARXY_REDUCTO_EXTRACTION_MODE=hybrid
PARXY_REDUCTO_TABLE_OUTPUT_FORMAT=md
```

## Supported Extraction Levels

| Level | Description |
|-------|-------------|
| `page` | Page-level text only — text items are concatenated per page |
| `block` | Page + individual blocks (`TextBlock`, `TableBlock`, `ImageBlock`) with bounding boxes |

```python
# Page-level extraction (default)
doc = Parxy.parse("document.pdf", driver_name="reducto", level="page")

# Block-level extraction
doc = Parxy.parse("document.pdf", driver_name="reducto", level="block")
```

## Input Types

The Reducto driver accepts all standard Parxy input types. Files are uploaded to the Reducto API before parsing.

### Local Files

```python
doc = Parxy.parse("/path/to/document.pdf", driver_name="reducto")
```

### URLs

```python
doc = Parxy.parse("https://example.com/report.pdf", driver_name="reducto")
```

## Per-Call Configuration Overrides

You can override any extraction option for a specific document by passing kwargs to `Parxy.parse()`. This is useful when most documents use the default configuration but some need different settings.

```python
from parxy_core.facade.parxy import Parxy

# Default configuration
doc1 = Parxy.parse("digital-pdf.pdf", driver_name="reducto")

# Use OCR for a scanned document
doc2 = Parxy.parse(
    "scanned-invoice.pdf",
    driver_name="reducto",
    extraction_mode="ocr",
)

# Extract tables as Markdown
doc3 = Parxy.parse(
    "report.pdf",
    driver_name="reducto",
    table_output_format="md",
)

# Process only a subset of pages
doc4 = Parxy.parse(
    "large-document.pdf",
    driver_name="reducto",
    page_range={"start": 1, "end": 5},
)

# Summarize figures using a vision model
doc5 = Parxy.parse(
    "illustrated-manual.pdf",
    driver_name="reducto",
    level="block",
    summarize_figures=True,
)
```

### Supported Per-Call Options

| Option | Type | Description |
|--------|------|-------------|
| `extraction_mode` | string | Text extraction mode (`hybrid` or `ocr`) |
| `table_output_format` | string | Table format (`html`, `json`, `md`, `jsonbbox`, `dynamic`, `csv`) |
| `page_range` | dict | Page range to process, e.g. `{"start": 1, "end": 5}` |
| `summarize_figures` | bool | Summarize figures using a vision model |

## Document Structure Roles

Reducto labels each extracted element with a block type. Parxy maps these to WAI-ARIA document structure roles:

| Reducto Type | WAI-ARIA Role | Description |
|--------------|---------------|-------------|
| `Title` | `doc-title` | Document title |
| `Section Header` | `heading` | Section headings |
| `Text` | `paragraph` | Main body text |
| `List Item` | `list` | List items |
| `Table` | `table` | Tables |
| `Figure` | `figure` | Images and figures |
| `Header` | `doc-pageheader` | Page headers |
| `Footer` | `doc-pagefooter` | Page footers |
| `Page Number` | `doc-pagefooter` | Page number elements |
| `Key Value` | `generic` | Key-value pairs |
| `Comment` | `generic` | Comments |
| `Signature` | `generic` | Signatures |

Access roles in your code:

```python
doc = Parxy.parse("document.pdf", driver_name="reducto", level="block")

for page in doc.pages:
    for block in page.blocks:
        print(f"Role: {block.role}, Category: {block.category}")
        if block.role == "heading":
            print(f"  Heading text: {block.text}")
```

## Bounding Boxes

Each block includes bounding box coordinates derived from the Reducto response:

```python
doc = Parxy.parse("document.pdf", driver_name="reducto", level="block")

for page in doc.pages:
    if page.blocks:
        for block in page.blocks:
            if block.bbox:
                print(f"  Block at ({block.bbox.x0:.1f}, {block.bbox.y0:.1f}) "
                      f"to ({block.bbox.x1:.1f}, {block.bbox.y1:.1f})")
```

## Parsing Metadata

Parxy exposes Reducto job metadata on the parsed document:

```python
doc = Parxy.parse("document.pdf", driver_name="reducto")

metadata = doc.parsing_metadata
print(f"Job ID: {metadata.get('job_id')}")
print(f"Upload file ID: {metadata.get('upload_file_id')}")
print(f"Duration: {metadata.get('duration')}s")
print(f"Pages: {metadata.get('num_pages')}")
print(f"Cost: {metadata.get('cost_estimation')} {metadata.get('cost_estimation_unit')}")
print(f"PDF URL: {metadata.get('pdf_url')}")
```

## Use Cases

### Scanned Documents

For image-based PDFs with no embedded text, use OCR extraction:

```python
doc = Parxy.parse(
    "scanned-contract.pdf",
    driver_name="reducto",
    extraction_mode="ocr",
)
```

### Documents with Complex Tables

Control how tables are serialised in the output:

```python
doc = Parxy.parse(
    "financial-report.pdf",
    driver_name="reducto",
    level="block",
    table_output_format="md",
)

for page in doc.pages:
    if page.blocks:
        for block in page.blocks:
            if block.role == "table":
                print(block.text)  # Markdown table
```

### Illustrated Documents

To generate descriptions for figures using a vision model:

```python
doc = Parxy.parse(
    "illustrated-guide.pdf",
    driver_name="reducto",
    level="block",
    summarize_figures=True,
)

from parxy_core.models import ImageBlock

for page in doc.pages:
    if page.blocks:
        for block in page.blocks:
            if isinstance(block, ImageBlock):
                print(f"Figure on page {page.number}: {block.alt_text}")
```

### Selective Page Extraction

Process only a specific range of pages from a large document:

```python
doc = Parxy.parse(
    "large-manual.pdf",
    driver_name="reducto",
    page_range={"start": 1, "end": 10},
)
```

### Filtering by Block Role

Extract only main body text, skipping headers and footers:

```python
doc = Parxy.parse("document.pdf", driver_name="reducto", level="block")

skip_roles = {"doc-pageheader", "doc-pagefooter"}
body_blocks = [
    block
    for page in doc.pages
    if page.blocks
    for block in page.blocks
    if block.role not in skip_roles
]
```

## Programmatic Configuration

You can configure the driver programmatically instead of using environment variables:

```python
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import ReductoConfig

config = ReductoConfig(
    api_key="your-api-key",
    environment="eu",
    extraction_mode="hybrid",
    table_output_format="md",
)

driver = Parxy.driver("reducto", config=config)
doc = driver.handle("document.pdf", level="block")
```

## Troubleshooting

### Authentication Errors

If you see `AuthenticationException`:

1. Verify your API key is correct and has not expired
2. Ensure `PARXY_REDUCTO_API_KEY` is set in your `.env` file or environment before starting your application
3. Check that your account has access to the Reducto Parse API

### Wrong Region

If requests are failing or slow due to routing, set the closest environment:

```bash
PARXY_REDUCTO_ENVIRONMENT=eu   # Europe
PARXY_REDUCTO_ENVIRONMENT=au   # Australia
```

Or point to a custom endpoint with `PARXY_REDUCTO_BASE_URL`.

### Timeout Errors

For large documents, the default SDK timeout may not be enough:

```bash
PARXY_REDUCTO_TIMEOUT=300
```

### Missing Text in Scanned PDFs

If extracted text is empty or incomplete for scanned pages, switch to OCR mode:

```python
doc = Parxy.parse("scanned.pdf", driver_name="reducto", extraction_mode="ocr")
```

## See Also

- [Reducto Documentation](https://docs.reducto.ai/)
- [Document Structure Roles](../explanation/document-roles.md)
- [Getting Started Tutorial](../tutorials/getting_started.md)

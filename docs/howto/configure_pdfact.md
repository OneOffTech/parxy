# How to Configure PdfAct

This guide shows you how to configure the PdfAct driver for document processing using a self-hosted or remote PdfAct service.

## Prerequisites

- Parxy installed (PdfAct is included in the base installation)
- A running PdfAct service instance (see [PdfAct](https://github.com/data-house/pdfact/) for setup)

## Quick Start

### Step 1: Start a PdfAct Service

PdfAct runs as a REST API service. You can run it locally using Docker:

```bash
docker run -p 4567:4567 ghcr.io/data-house/pdfact:main
```

### Step 2: Configure the Base URL

If running locally on the default port, no configuration is needed. Otherwise, create a `.env` file:

```bash
PARXY_PDFACT_BASE_URL=http://your-pdfact-server:4567/
```

Or set it as an environment variable:

```bash
export PARXY_PDFACT_BASE_URL=http://your-pdfact-server:4567/
```

### Step 3: Parse a Document

```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf", driver_name="pdfact")
print(f"Processed {len(doc.pages)} pages")
```

## Configuration Options

PdfAct configuration is minimal compared to cloud-based services since it's typically self-hosted.

### Environment Variables

All PdfAct configuration uses environment variables with the `PARXY_PDFACT_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_PDFACT_BASE_URL` | string | `http://localhost:4567/` | The base URL of the PdfAct API |
| `PARXY_PDFACT_API_KEY` | string | None | Authentication key (if your PdfAct instance requires it) |

## Supported Extraction Levels

PdfAct supports the following extraction levels:

| Level | Description |
|-------|-------------|
| `page` | Extract text at page level only |
| `paragraph` | Extract text as paragraphs (alias for block) |
| `block` | Extract text as blocks with layout and style information |

```python
# Page-level extraction
doc = Parxy.parse("document.pdf", driver_name="pdfact", level="page")

# Block-level extraction (default)
doc = Parxy.parse("document.pdf", driver_name="pdfact", level="block")
```

## Input Types

PdfAct accepts two types of input:

### Local Files

```python
doc = Parxy.parse("/path/to/document.pdf", driver_name="pdfact")
```

### URLs

```python
doc = Parxy.parse("https://example.com/document.pdf", driver_name="pdfact")
```

**Note**: BytesIO and bytes inputs are not currently supported by the PdfAct driver.

## Document Structure Roles

PdfAct extracts semantic roles from documents. Parxy maps these to WAI-ARIA document structure roles for standardized output:

| PdfAct Category | WAI-ARIA Role | Description |
|-----------------|---------------|-------------|
| `body` | `paragraph` | Main body text |
| `heading` | `heading` | Section headings |
| `title` | `doc-title` | Document title |
| `subtitle` | `doc-subtitle` | Document subtitle |
| `abstract` | `doc-abstract` | Document abstract |
| `caption` | `caption` | Figure/table captions |
| `figure` | `figure` | Figures and images |
| `table` | `table` | Tables |
| `formula` | `math` | Mathematical formulas |
| `reference` | `doc-biblioref` | Bibliography references |
| `footnote` | `doc-footnote` | Footnotes |
| `toc` | `doc-toc` | Table of contents |
| `appendix` | `doc-appendix` | Appendix sections |
| `itemize-item` | `listitem` | List items |
| `header` | `doc-pageheader` | Page headers |
| `footer` | `doc-pagefooter` | Page footers |

Access the role in your code:

```python
doc = Parxy.parse("document.pdf", driver_name="pdfact")

for page in doc.pages:
    for block in page.blocks:
        print(f"Role: {block.role}, Text: {block.text[:50]}...")
```

## Style Information

PdfAct extracts rich style information for each text block:

```python
doc = Parxy.parse("document.pdf", driver_name="pdfact")

for page in doc.pages:
    for block in page.blocks:
        if block.style:
            print(f"Font: {block.style.font_name}")
            print(f"Size: {block.style.font_size}")
            print(f"Color: {block.style.color}")
            print(f"Style: {block.style.font_style}")  # e.g., 'italic'
            print(f"Weight: {block.style.weight}")     # e.g., 400 for bold
```

## Bounding Box Information

Each text block includes bounding box coordinates:

```python
doc = Parxy.parse("document.pdf", driver_name="pdfact")

for page in doc.pages:
    print(f"Page dimensions: {page.width} x {page.height}")
    for block in page.blocks:
        if block.bbox:
            print(f"Block at: ({block.bbox.x0}, {block.bbox.y0}) to ({block.bbox.x1}, {block.bbox.y1})")
```

## Use Cases

### Scientific Papers

PdfAct excels at extracting structured content from scientific papers:

```python
doc = Parxy.parse("paper.pdf", driver_name="pdfact")

# Find abstract
for page in doc.pages:
    for block in page.blocks:
        if block.role == "doc-abstract":
            print(f"Abstract: {block.text}")

# Find references
for page in doc.pages:
    for block in page.blocks:
        if block.role == "doc-biblioref":
            print(f"Reference: {block.text}")
```

### Processing Remote PDFs

When processing PDFs from URLs, PdfAct handles the download internally:

```python
doc = Parxy.parse(
    "https://arxiv.org/pdf/2301.00001.pdf",
    driver_name="pdfact"
)
```

### Filtering by Content Type

Filter blocks by their semantic role:

```python
doc = Parxy.parse("document.pdf", driver_name="pdfact")

# Get only main body text (no headers, footers, footnotes)
body_text = []
skip_roles = {"doc-pageheader", "doc-pagefooter", "doc-footnote"}

for page in doc.pages:
    for block in page.blocks:
        if block.role not in skip_roles:
            body_text.append(block.text)

clean_text = "\n".join(body_text)
```

## Self-Hosting PdfAct

### Docker Deployment

The simplest way to run PdfAct is using Docker.

```bash
# Basic deployment
docker run -d -p 4567:4567 --name pdfact ghcr.io/data-house/pdfact:main

# With resource limits
docker run -d -p 4567:4567 --name pdfact \
    --memory="4g" \
    --cpus="2" \
    ghcr.io/data-house/pdfact:main
```

### Docker Compose

Parxy offers the `parxy docker` command to generate a Docker Compose file for deploying PdfAct

## Troubleshooting

### Connection Errors

If you see connection errors:

1. Verify PdfAct is running: `curl http://localhost:4567/`
2. Check the base URL configuration
3. Ensure no firewall blocks the port

```python
# Test connection
import requests

try:
    response = requests.get("http://localhost:4567/")
    print(f"PdfAct status: {response.status_code}")
except requests.ConnectionError:
    print("Cannot connect to PdfAct service")
```

### Invalid URL Errors

The driver validates URLs before connecting:

```python
# This will raise ValueError
try:
    config = PdfActConfig(base_url="not-a-valid-url")
except ValueError as e:
    print(f"Invalid URL: {e}")
```

### Unsupported Input Types

BytesIO and bytes inputs are not supported:

```python
# This will raise NotImplementedError
import io

with open("document.pdf", "rb") as f:
    data = io.BytesIO(f.read())

try:
    doc = Parxy.parse(data, driver_name="pdfact")
except NotImplementedError:
    print("Use file path or URL instead")
```

### Missing Text

If text is missing from output:

1. Verify the PDF contains extractable text (not just images)
2. Check if PdfAct logs show parsing errors
3. Try with a different PDF to isolate the issue

## See Also

- [PdfAct GitHub Repository](https://github.com/data-house/pdfact)
- [Document Structure Roles](../explanation/document-roles.md)
- [Getting Started Tutorial](../tutorials/getting_started.md)

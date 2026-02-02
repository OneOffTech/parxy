# How to Configure LandingAI ADE

This guide shows you how to configure the LandingAI ADE (Agentic Document Extraction) driver for document processing, including setting default options and overriding them on a per-document basis.

## Prerequisites

- Parxy installed with LandingAI support: `pip install parxy[landingai]` or via UV `uv add parxy[landingai]`
- A LandingAI API key from [LandingAI](https://landing.ai/)

## Quick Start

### Step 1: Set Your API Key

Create a `.env` file in your project directory:

```bash
PARXY_LANDINGAI_API_KEY=your-api-key-here
```

Or set it as an environment variable:

```bash
export PARXY_LANDINGAI_API_KEY=your-api-key-here
```

### Step 2: Parse a Document

```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf", driver_name="landingai")
print(f"Processed {len(doc.pages)} pages")
```

## Configuration Options

LandingAI ADE supports configuration options that control API connectivity. These can be set via environment variables or programmatic configuration.

### Environment Variables

All LandingAI configuration uses environment variables with the `PARXY_LANDINGAI_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LANDINGAI_API_KEY` | string | None | Your LandingAI API key |
| `PARXY_LANDINGAI_ENVIRONMENT` | string | `eu` | API environment (`production` or `eu`) |
| `PARXY_LANDINGAI_BASE_URL` | string | None | Custom API endpoint (overrides environment) |

### Environment Options

LandingAI offers two hosted environments:

| Environment | API Endpoint | Description |
|-------------|--------------|-------------|
| `production` | `https://api.va.landing.ai` | US-based production environment |
| `eu` | `https://api.va.eu-west-1.landing.ai` | EU-based environment (default) |

To use the US production environment:

```bash
PARXY_LANDINGAI_ENVIRONMENT=production
```

### Custom Base URL

If you need to use a custom endpoint (e.g., self-hosted or enterprise deployment), set the base URL directly and set environment to `None`:

```bash
PARXY_LANDINGAI_BASE_URL=https://your-custom-endpoint.example.com
PARXY_LANDINGAI_ENVIRONMENT=
```

## Document Structure and Roles

LandingAI ADE extracts structured content from documents and categorizes each chunk by type. Parxy maps these types to WAI-ARIA document structure roles for semantic understanding.

### Chunk Type Mappings

| LandingAI Type | Parxy Role | Description |
|----------------|------------|-------------|
| `text` | `paragraph` | Regular text content |
| `table` | `table` | Tabular data |
| `figure` | `figure` | Images and diagrams |
| `logo` | `figure` | Company logos (DPT-2 model) |
| `card` | `figure` | ID cards, driver licenses (DPT-2 model) |
| `attestation` | `figure` | Signatures, stamps, seals (DPT-2 model) |
| `scan_code` | `figure` | QR codes, barcodes (DPT-2 model) |
| `marginalia` | `generic` | Mixed content in margins |
| `heading` | `heading` | Section headings |
| `title` | `doc-title` | Document title |
| `subtitle` | `doc-subtitle` | Document subtitle |
| `chapter` | `doc-chapter` | Chapter markers |
| `page-header` / `header` | `doc-pageheader` | Page headers |
| `page-footer` / `footer` | `doc-pagefooter` | Page footers |
| `page-number` | `doc-pagefooter` | Page numbers |
| `footnote` / `note` | `doc-footnote` | Footnotes |
| `endnote` | `doc-endnotes` | Endnotes |

## Programmatic Configuration

You can configure the driver programmatically:

```python
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import LandingAIConfig

# Create custom configuration for EU environment
config = LandingAIConfig(
    api_key="your-api-key",
    environment="eu",
)

# Get driver with custom config
driver = Parxy.driver("landingai", config=config)

# Parse documents
doc = driver.handle("document.pdf", level="block")
```

### Using US Production Environment

```python
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import LandingAIConfig

config = LandingAIConfig(
    api_key="your-api-key",
    environment="production",  # Use US endpoint
)

driver = Parxy.driver("landingai", config=config)
doc = driver.handle("document.pdf")
```

### Using Custom Endpoint

```python
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import LandingAIConfig

config = LandingAIConfig(
    api_key="your-api-key",
    environment=None,  # Disable default environment
    base_url="https://your-custom-endpoint.example.com",
)

driver = Parxy.driver("landingai", config=config)
doc = driver.handle("document.pdf")
```

## Cost Estimation

Parxy automatically tracks parsing costs in the document metadata:

```python
doc = Parxy.parse("document.pdf", driver_name="landingai")

# Access cost information
metadata = doc.parsing_metadata
print(f"Credit usage: {metadata.get('cost_estimation')} {metadata.get('cost_estimation_unit')}")
```

## Document Metadata

After parsing, the document contains additional metadata from LandingAI ADE:

```python
doc = Parxy.parse("document.pdf", driver_name="landingai")

metadata = doc.parsing_metadata

# ADE-specific details
details = metadata.get('ade_details', {})
print(f"Processing time: {details.get('duration_ms')} ms")
print(f"Job ID: {details.get('job_id')}")
print(f"Page count: {details.get('page_count')}")
print(f"API version: {details.get('version')}")
print(f"Filename: {details.get('filename')}")

# Check for any failed pages (partial content)
if 'failed_pages' in details:
    print(f"Failed pages: {details.get('failed_pages')}")
```

## Working with Extracted Content

### Accessing Blocks by Role

```python
doc = Parxy.parse("document.pdf", driver_name="landingai")

for page in doc.pages:
    # Get all tables
    tables = [b for b in page.blocks if b.role == 'table']

    # Get all headings
    headings = [b for b in page.blocks if b.role == 'heading']

    # Get document title
    titles = [b for b in page.blocks if b.role == 'doc-title']

    # Get figures (images, logos, etc.)
    figures = [b for b in page.blocks if b.role == 'figure']

    print(f"Page {page.number}: {len(tables)} tables, {len(headings)} headings")
```

### Accessing Bounding Boxes

LandingAI ADE provides bounding box coordinates for each extracted chunk:

```python
doc = Parxy.parse("document.pdf", driver_name="landingai")

for page in doc.pages:
    for block in page.blocks:
        if block.bbox:
            print(f"Block at ({block.bbox.x0}, {block.bbox.y0}) - ({block.bbox.x1}, {block.bbox.y1})")
            print(f"  Type: {block.category}")
            print(f"  Role: {block.role}")
            print(f"  Text: {block.text[:50]}...")
```

### Accessing Original Chunk Data

The original LandingAI chunk data is preserved in `source_data`:

```python
doc = Parxy.parse("document.pdf", driver_name="landingai")

for page in doc.pages:
    for block in page.blocks:
        original = block.source_data
        # Access any LandingAI-specific fields
        print(f"Original type: {original.get('type')}")
        print(f"Markdown: {original.get('markdown')}")
```

## Troubleshooting

### Authentication Errors

If you see authentication errors:

1. Verify your API key is correct
2. Check the key has not expired
3. Ensure you're using the correct environment for your account

```python
# Test authentication
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import LandingAIConfig

config = LandingAIConfig(api_key="your-key", environment="eu")
driver = Parxy.driver("landingai", config=config)
# If no error, authentication is working
```

### Rate Limiting

If you encounter 429 errors (rate limiting):

1. Reduce the frequency of API calls
2. Implement retry logic with exponential backoff
3. Contact LandingAI for higher rate limits if needed

### Quota Exceeded

If you see 402 errors (quota exceeded):

1. Check your account's remaining credits
2. Purchase additional credits from LandingAI

### Input Validation Errors

If you see 422 errors (input validation):

1. Ensure the file format is supported (PDF, images)
2. Check the file is not corrupted
3. Verify the file size is within limits

### Partial Content / Failed Pages

If some pages fail to process:

```python
doc = Parxy.parse("document.pdf", driver_name="landingai")

details = doc.parsing_metadata.get('ade_details', {})
if 'failed_pages' in details:
    failed = details['failed_pages']
    print(f"Warning: Pages {failed} failed to process")
```

This can happen with:
- Corrupted pages
- Pages with unsupported content
- Processing timeouts on complex pages

### Wrong Environment

If API calls fail with connection errors:

1. Verify the environment setting matches your account region
2. Try explicitly setting the base URL
3. Check network connectivity to the LandingAI API

## See Also

- [LandingAI ADE Documentation](https://docs.landing.ai/ade/)
- [LandingAI ADE JSON Response](https://docs.landing.ai/ade/ade-json-response.md)
- [Document Structure Roles](../explanation/document-roles.md)
- [Getting Started Tutorial](../tutorials/getting_started.md)

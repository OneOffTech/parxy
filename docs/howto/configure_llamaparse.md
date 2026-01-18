# How to Configure LlamaParse

This guide shows you how to configure the LlamaParse driver for document processing, including setting default options and overriding them on a per-document basis.

## Prerequisites

- Parxy installed with LlamaParse support: `pip install parxy[llama]` or via UV `uv add parxy[llama]`
- A LlamaParse API key from [LlamaIndex Cloud](https://cloud.llamaindex.ai/)

## Quick Start

### Step 1: Set Your API Key

Create a `.env` file in your project directory:

```bash
PARXY_LLAMAPARSE_API_KEY=llx-your-api-key-here
```

Or set it as an environment variable:

```bash
export PARXY_LLAMAPARSE_API_KEY=llx-your-api-key-here
```

### Step 2: Parse a Document

```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf", driver_name="llamaparse")
print(f"Processed {len(doc.pages)} pages")
```

## Configuration Options

LlamaParse supports extensive configuration options that control parsing behavior. These can be set at two levels:

1. **Default configuration** - Applied to all documents via environment variables or config
2. **Per-call overrides** - Applied to specific documents via kwargs

### Environment Variables

All LlamaParse configuration uses environment variables with the `PARXY_LLAMAPARSE_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_API_KEY` | string | None | Your LlamaParse API key |
| `PARXY_LLAMAPARSE_BASE_URL` | string | `https://api.cloud.eu.llamaindex.ai` | API endpoint |
| `PARXY_LLAMAPARSE_ORGANIZATION_ID` | string | None | Organization ID for usage tracking |
| `PARXY_LLAMAPARSE_PROJECT_ID` | string | None | Project ID for organization |

#### Client Behavior

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_NUM_WORKERS` | int | `4` | Number of concurrent API workers |
| `PARXY_LLAMAPARSE_SHOW_PROGRESS` | bool | `False` | Show progress for multi-file parsing |
| `PARXY_LLAMAPARSE_VERBOSE` | bool | `False` | Print parsing progress |

#### Parsing Mode

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_PARSE_MODE` | string | `parse_page_with_llm` | Parsing mode (see below) |
| `PARXY_LLAMAPARSE_PRESET` | string | None | Parser preset (overrides most options) |
| `PARXY_LLAMAPARSE_MODEL` | string | None | Document model for `parse_with_agent` mode |
| `PARXY_LLAMAPARSE_PREMIUM_MODE` | bool | `False` | Use best parser mode |
| `PARXY_LLAMAPARSE_FAST_MODE` | bool | `False` | Fast mode (skips OCR and reconstruction) |

#### OCR and Extraction

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_DISABLE_OCR` | bool | `False` | Disable OCR (extract copyable text only) |
| `PARXY_LLAMAPARSE_DISABLE_IMAGE_EXTRACTION` | bool | `False` | Don't extract images (faster) |
| `PARXY_LLAMAPARSE_HIGH_RES_OCR` | bool | `False` | High resolution OCR (slower but more accurate) |
| `PARXY_LLAMAPARSE_EXTRACT_LAYOUT` | bool | `False` | Extract layout information (1 credit/page) |

#### Text Handling

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_SKIP_DIAGONAL_TEXT` | bool | `False` | Skip diagonal/rotated text |
| `PARXY_LLAMAPARSE_LANGUAGE` | string | `en` | Document language |
| `PARXY_LLAMAPARSE_DO_NOT_UNROLL_COLUMNS` | bool | `False` | Preserve column layout |

#### Page Selection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_TARGET_PAGES` | string | None | Pages to extract (e.g., `0,2,5-10`) |
| `PARXY_LLAMAPARSE_MAX_PAGES` | int | None | Maximum pages to extract |

#### Advanced Features

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_CONTINUOUS_MODE` | bool | `False` | Better handling of tables across pages |
| `PARXY_LLAMAPARSE_AUTO_MODE` | bool | `False` | Auto-select mode based on content |
| `PARXY_LLAMAPARSE_DO_NOT_CACHE` | bool | `True` | Disable result caching |

### Parsing Modes

LlamaParse offers several parsing modes with different accuracy and cost trade-offs:

| Mode | Credits/Page | Description |
|------|--------------|-------------|
| `parse_page_without_llm` | 1 | Fast extraction without LLM enhancement |
| `accurate` / `parse_page_with_llm` | 3 | LLM-enhanced extraction (recommended) |
| `parse_page_with_lvm` | 6 | Vision model for complex layouts |
| `parse_page_with_agent` | 10 | Agent-based extraction for complex documents |
| `parse_document_with_llm` | 30 | Document-level LLM processing |
| `parse_document_with_agent` | 30 | Document-level agent processing |

## Per-Call Configuration Overrides

You can override default configuration for specific documents by passing kwargs to `Parxy.parse()`:

```python
from parxy_core.facade.parxy import Parxy

# Use default configuration
doc1 = Parxy.parse("simple.pdf", driver_name="llamaparse")

# Override for a specific document
doc2 = Parxy.parse(
    "complex-cad-drawing.pdf",
    driver_name="llamaparse",
    skip_diagonal_text=True,  # Skip rotated text in CAD drawings
    high_res_ocr=True,        # Better accuracy for small text
)

# Different parsing mode for tables
doc3 = Parxy.parse(
    "financial-report.pdf",
    driver_name="llamaparse",
    parse_mode="parse_page_with_lvm",  # Vision model for complex tables
    continuous_mode=True,               # Handle tables spanning pages
)

# Parse only specific pages
doc4 = Parxy.parse(
    "large-document.pdf",
    driver_name="llamaparse",
    target_pages="0,5-10,15",  # Only pages 0, 5-10, and 15
    max_pages=20,              # Stop after 20 pages regardless
)
```

### Supported Per-Call Options

The following options can be overridden per-call:

- `model` - Document model for parse_with_agent
- `skip_diagonal_text` - Skip diagonal/rotated text
- `preset` - Parser preset
- `parse_mode` - Parsing mode
- `language` - Text language
- `target_pages` - Specific pages to parse
- `max_pages` - Maximum pages to extract
- `continuous_mode` - Better table handling across pages
- `disable_ocr` - Disable OCR
- `disable_image_extraction` - Don't extract images
- `fast_mode` - Speed over accuracy
- `premium_mode` - Best parser mode
- `high_res_ocr` - High resolution OCR
- `extract_layout` - Extract layout information
- `auto_mode` - Automatic mode selection
- `do_not_unroll_columns` - Preserve column layout

## Use Cases

### CAD Drawings and Technical Documents

CAD drawings often have diagonal text labels that can interfere with extraction:

```python
doc = Parxy.parse(
    "blueprint.pdf",
    driver_name="llamaparse",
    skip_diagonal_text=True,
    high_res_ocr=True,
    language="en",
)
```

### Financial Reports with Complex Tables

Financial documents often have tables that span multiple pages:

```python
doc = Parxy.parse(
    "annual-report.pdf",
    driver_name="llamaparse",
    parse_mode="parse_page_with_lvm",
    continuous_mode=True,
    extract_layout=True,
)
```

### Multi-Language Documents

For documents in languages other than English:

```python
doc = Parxy.parse(
    "document-german.pdf",
    driver_name="llamaparse",
    language="de",
)
```

### Large Documents with Selective Extraction

When you only need specific pages from a large document:

```python
doc = Parxy.parse(
    "large-manual.pdf",
    driver_name="llamaparse",
    target_pages="0-5,50-60",  # Table of contents and specific chapter
    max_pages=20,
)
```

### Speed-Optimized Processing

When speed is more important than accuracy:

```python
doc = Parxy.parse(
    "simple-text.pdf",
    driver_name="llamaparse",
    fast_mode=True,
    disable_image_extraction=True,
    parse_mode="parse_page_without_llm",
)
```

### Quality-Optimized Processing

When accuracy is critical:

```python
doc = Parxy.parse(
    "legal-contract.pdf",
    driver_name="llamaparse",
    premium_mode=True,
    high_res_ocr=True,
)
```

## Programmatic Configuration

You can also configure the driver programmatically:

```python
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import LlamaParseConfig

# Create custom configuration
config = LlamaParseConfig(
    api_key="llx-your-api-key",
    parse_mode="parse_page_with_llm",
    language="en",
    continuous_mode=True,
)

# Get driver with custom config
driver = Parxy.driver("llamaparse", config=config)

# Parse documents
doc = driver.handle("document.pdf", level="block")
```

## Cost Estimation

Parxy automatically tracks parsing costs in the document metadata:

```python
doc = Parxy.parse("document.pdf", driver_name="llamaparse")

# Access cost information
metadata = doc.parsing_metadata
print(f"Estimated cost: {metadata.get('cost_estimation')} {metadata.get('cost_estimation_unit')}")
print(f"Parsing modes used: {metadata.get('parsing_mode_counts')}")
```

If you configure `PARXY_LLAMAPARSE_ORGANIZATION_ID`, Parxy will fetch actual usage metrics from the LlamaParse API for more accurate cost tracking.

## Troubleshooting

### Authentication Errors

If you see 401/403 errors:

1. Verify your API key is correct
2. Check the key has not expired
3. Ensure the key has access to the requested features

```python
# Test authentication
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import LlamaParseConfig

config = LlamaParseConfig(api_key="llx-your-key")
driver = Parxy.driver("llamaparse", config=config)
# If no error, authentication is working
```

### Slow Processing

If parsing is slow:

1. Use `fast_mode=True` for simple documents
2. Disable image extraction if not needed
3. Use `parse_page_without_llm` mode for basic text
4. Limit pages with `target_pages` or `max_pages`

### Missing Text

If text is missing from output:

1. Enable `high_res_ocr=True` for scanned documents
2. Try `premium_mode=True` for better accuracy
3. Check if text is diagonal (`skip_diagonal_text=False`)
4. Use appropriate `language` setting

### Tables Not Extracted Correctly

For table extraction issues:

1. Enable `continuous_mode=True` for multi-page tables
2. Use `parse_mode="parse_page_with_lvm"` for complex tables
3. Enable `extract_layout=True` for layout information

## See Also

- [LlamaParse Documentation](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/)
- [LlamaIndex Cloud Pricing](https://developers.llamaindex.ai/python/cloud/general/pricing/)
- [Getting Started Tutorial](../tutorials/getting_started.md)

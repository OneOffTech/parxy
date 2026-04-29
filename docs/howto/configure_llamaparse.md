---
title: Configure LlamaParse
description: How to set up the LlamaParse driver, configure the API key and parsing tier, and override options on a per-document basis for better extraction results.
---

# How to Configure LlamaParse

This guide shows you how to configure the LlamaParse driver for document processing, including setting default options and overriding them on a per-document basis.

## Prerequisites

- Parxy installed with LlamaParse support: `pip install parxy[llama]` or via UV `uv add parxy[llama]`
- A LlamaParse API key from [LlamaIndex Cloud](https://cloud.llamaindex.ai/)

> **Upgrade note (llama-cloud v2):** Parxy now uses the `llama-cloud` v2 SDK (previously `llama-cloud-services`). This brings a new API with breaking changes described in the [Upgrade Guide](#upgrade-guide-from-v1) at the bottom of this page.

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

1. **Default configuration** — Applied to all documents via environment variables or config object
2. **Per-call overrides** — Applied to specific documents via kwargs

### Environment Variables

All LlamaParse configuration uses environment variables with the `PARXY_LLAMAPARSE_` prefix:

#### Connection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_API_KEY` | string | None | Your LlamaParse API key |
| `PARXY_LLAMAPARSE_BASE_URL` | string | `https://api.cloud.eu.llamaindex.ai` | API endpoint (override for region or self-hosted) |
| `PARXY_LLAMAPARSE_ORGANIZATION_ID` | string | None | Organization ID for usage tracking |
| `PARXY_LLAMAPARSE_PROJECT_ID` | string | None | Project ID |

#### Parsing Tier

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_TIER` | string | `cost_effective` | Parsing tier: `fast`, `cost_effective`, `agentic`, `agentic_plus` |
| `PARXY_LLAMAPARSE_VERSION` | string | `latest` | Tier version. Use `latest` or a specific date string for reproducibility |
| `PARXY_LLAMAPARSE_PARSE_MODE` | string | None | Legacy mode name (automatically mapped to a tier — see below) |
| `PARXY_LLAMAPARSE_PREMIUM_MODE` | bool | `False` | Shorthand for `tier=agentic_plus` |
| `PARXY_LLAMAPARSE_FAST_MODE` | bool | `False` | Shorthand for `tier=fast` |

#### OCR and Extraction

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_DISABLE_OCR` | bool | `False` | Disable OCR on embedded images |
| `PARXY_LLAMAPARSE_DISABLE_IMAGE_EXTRACTION` | bool | `False` | Skip image extraction (faster) |
| `PARXY_LLAMAPARSE_SKIP_DIAGONAL_TEXT` | bool | `False` | Skip diagonal/rotated text |
| `PARXY_LLAMAPARSE_LANGUAGE` | string | `en` | Primary OCR language |

#### Output and Layout

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_DO_NOT_UNROLL_COLUMNS` | bool | `False` | Preserve multi-column layout |
| `PARXY_LLAMAPARSE_CONTINUOUS_MODE` | bool | `False` | Merge tables that span multiple pages |

#### Page Selection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_TARGET_PAGES` | string | None | Pages to extract — comma-separated **1-based** page numbers or ranges (e.g. `1,3,5-8`) |
| `PARXY_LLAMAPARSE_MAX_PAGES` | int | None | Maximum pages to extract |

#### Caching and Behavior

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLAMAPARSE_DO_NOT_CACHE` | bool | `True` | Bypass result caching |
| `PARXY_LLAMAPARSE_VERBOSE` | bool | `False` | Print progress indicators during parsing |

### Parsing Tiers

The LlamaParse v2 API uses **tiers** instead of the old `parse_mode` strings:

| Tier | Credits/Page | Description |
|------|-------------|-------------|
| `fast` | 1 | Rule-based extraction, no AI, fastest and cheapest |
| `cost_effective` | 3 | Balanced quality and cost — **recommended default** |
| `agentic` | 6 | Full AI-powered parsing for complex layouts |
| `agentic_plus` | 10 | Premium AI with the highest accuracy |

```python
from parxy_core.facade.parxy import Parxy

# Use the default tier (cost_effective)
doc = Parxy.parse("document.pdf", driver_name="llamaparse")

# Use a specific tier
doc = Parxy.parse("document.pdf", driver_name="llamaparse", tier="agentic")
```

## Per-Call Configuration Overrides

You can override default configuration for specific documents by passing kwargs to `Parxy.parse()`:

```python
from parxy_core.facade.parxy import Parxy

# Use default configuration
doc1 = Parxy.parse("simple.pdf", driver_name="llamaparse")

# Use agentic tier for a complex document
doc2 = Parxy.parse(
    "complex-cad-drawing.pdf",
    driver_name="llamaparse",
    tier="agentic",
    skip_diagonal_text=True,
)

# Merge tables across pages
doc3 = Parxy.parse(
    "financial-report.pdf",
    driver_name="llamaparse",
    tier="agentic",
    continuous_mode=True,
)

# Parse only specific pages
doc4 = Parxy.parse(
    "large-document.pdf",
    driver_name="llamaparse",
    target_pages="1,6-11,16",  # 1-based page numbers
    max_pages=20,
)
```

### Supported Per-Call Options

| Option | Description |
|--------|-------------|
| `tier` | Parsing tier (`fast`, `cost_effective`, `agentic`, `agentic_plus`) |
| `version` | API version string (default `latest`) |
| `parse_mode` | Legacy mode name — mapped to a tier automatically |
| `premium_mode` | If `True`, uses `agentic_plus` tier |
| `fast_mode` | If `True`, uses `fast` tier |
| `language` | OCR language code |
| `target_pages` | Specific pages (1-based, e.g. `'1,3,5-8'`) |
| `max_pages` | Maximum pages to extract |
| `skip_diagonal_text` | Skip text rotated at an angle |
| `do_not_unroll_columns` | Keep multi-column layout intact |
| `disable_image_extraction` | Skip image extraction |
| `disable_ocr` | Disable OCR on images |
| `continuous_mode` | Merge tables that span multiple pages |
| `do_not_cache` | Bypass result caching |

## Use Cases

### CAD Drawings and Technical Documents

CAD drawings often have diagonal text labels that can interfere with extraction:

```python
doc = Parxy.parse(
    "blueprint.pdf",
    driver_name="llamaparse",
    tier="agentic",
    skip_diagonal_text=True,
    language="en",
)
```

### Financial Reports with Complex Tables

Financial documents often have tables that span multiple pages:

```python
doc = Parxy.parse(
    "annual-report.pdf",
    driver_name="llamaparse",
    tier="agentic",
    continuous_mode=True,
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
    target_pages="1-6,51-61",  # Table of contents and specific chapter (1-based)
    max_pages=20,
)
```

### Speed-Optimized Processing

When speed is more important than accuracy:

```python
doc = Parxy.parse(
    "simple-text.pdf",
    driver_name="llamaparse",
    tier="fast",
    disable_image_extraction=True,
)
```

### Quality-Optimized Processing

When accuracy is critical:

```python
doc = Parxy.parse(
    "legal-contract.pdf",
    driver_name="llamaparse",
    tier="agentic_plus",
)
```

## Programmatic Configuration

You can also configure the driver programmatically:

```python
from parxy_core.facade.parxy import Parxy
from parxy_core.models.config import LlamaParseConfig

config = LlamaParseConfig(
    api_key="llx-your-api-key",
    tier="cost_effective",
    language="en",
    continuous_mode=True,
)

driver = Parxy.driver("llamaparse", config=config)
doc = driver.handle("document.pdf", level="block")
```

## Cost Estimation

Parxy automatically tracks parsing costs in the document metadata:

```python
doc = Parxy.parse("document.pdf", driver_name="llamaparse")

metadata = doc.parsing_metadata
print(f"Job ID: {metadata.get('job_id')}")
print(f"Tier used: {metadata.get('tier')}")
print(f"Estimated cost: {metadata.get('cost_estimation')} {metadata.get('cost_estimation_unit')}")
```

If you configure `PARXY_LLAMAPARSE_ORGANIZATION_ID`, Parxy will fetch actual usage metrics from the LlamaParse API for more accurate cost tracking.

## Troubleshooting

### Authentication Errors

If you see 401/403 errors:

1. Verify your API key is correct
2. Check the key has not expired
3. Ensure the key has access to the requested tier

### Slow Processing

If parsing is slow:

1. Use `tier="fast"` for simple text-based documents
2. Disable image extraction with `disable_image_extraction=True`
3. Limit pages with `target_pages` or `max_pages`

### Missing Text

If text is missing from output:

1. Try a higher tier (`agentic` or `agentic_plus`) for better accuracy on complex layouts
2. Disable diagonal text filtering if you need angled text (`skip_diagonal_text=False`)
3. Set the appropriate `language` for non-English documents

### Tables Not Extracted Correctly

For table extraction issues:

1. Enable `continuous_mode=True` for multi-page tables
2. Use `tier="agentic"` or `tier="agentic_plus"` for complex table layouts

---

## Upgrade Guide from v1

This section covers what changed when upgrading from `llama-cloud-services` (API v1) to `llama-cloud` v2.

### Dependency Change

```toml
# Before (pyproject.toml)
llama = ["llama-cloud-services>=..."]

# After
llama = ["llama-cloud>=2.0.0"]
```

### Parsing Tiers Replace Parse Modes

The `parse_mode` string was replaced by the `tier` field. Existing `parse_mode` values are still accepted and automatically mapped — no code change required. For new code, prefer `tier` directly:

| Old `parse_mode` | New `tier` |
|------------------|-----------|
| `parse_page_without_llm` | `fast` |
| `parse_page_with_llm` | `cost_effective` |
| `accurate` | `cost_effective` |
| `parse_page_with_lvm` | `agentic` |
| `parse_page_with_agent` | `agentic` |
| `parse_document_with_llm` | `agentic` |
| `parse_document_with_agent` | `agentic_plus` |

```python
# Before (mapped automatically to tier)
Parxy.parse("doc.pdf", driver_name="llamaparse", parse_mode="parse_page_with_lvm")

# After (preferred)
Parxy.parse("doc.pdf", driver_name="llamaparse", tier="agentic")
```

### `target_pages` Indexing Changed to 1-Based

The old API used **0-based** page indexing. The new API uses **1-based** indexing:

```python
# Before (0-based)
Parxy.parse("doc.pdf", driver_name="llamaparse", target_pages="0,2,5-10")

# After (1-based)
Parxy.parse("doc.pdf", driver_name="llamaparse", target_pages="1,3,6-11")
```

### Removed Options

The following options are no longer supported by the API and have been removed from `LlamaParseConfig`. Passing them as kwargs or environment variables is silently ignored.

| Removed option | Reason |
|----------------|--------|
| `num_workers` | Not applicable — the v2 REST client manages concurrency internally |
| `show_progress` | Not applicable to the v2 REST client |
| `preset` | No equivalent in the v2 API |
| `model` | No equivalent in the v2 API |
| `high_res_ocr` | No direct equivalent in the v2 API |
| `extract_layout` | No direct equivalent in the v2 API |
| `auto_mode` | No direct equivalent in the v2 API |

### `parsing_metadata` Structure Changed

The `parsing_metadata` dictionary on parsed documents has a different shape:

```python
# Before
metadata = {
    "job_id": "...",
    "job_metadata": "<json string>",   # was a JSON-serialised string
    "job_error": "...",
    "job_error_code": "...",
    "job_status": "...",
    "page_parsing_modes": {1: "parse_page_with_llm", ...},
    "parsing_mode_counts": {"parse_page_with_llm": 3},
    "cost_estimation": 9,
    "cost_estimation_unit": "credits",
    "cost_data_source": "estimation",
}

# After
metadata = {
    "job_id": "...",
    "job_metadata": {...},             # now a plain dict
    "job_error": "...",                # error_message from job object
    "job_status": "COMPLETED",        # COMPLETED | FAILED | CANCELLED
    "tier": "cost_effective",         # the tier used for this parse
    "cost_estimation": 3,
    "cost_estimation_unit": "credits",
    "cost_data_source": "estimation", # or "beta_api" when organization_id is set
}
```

`page_parsing_modes` is no longer populated because the v2 API applies a single tier to the job, not per-page modes.

## See Also

- [LlamaParse Documentation](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/)
- [LlamaIndex Cloud Pricing](https://developers.llamaindex.ai/python/cloud/general/pricing/)
- [Getting Started Tutorial](../tutorials/getting_started.md)

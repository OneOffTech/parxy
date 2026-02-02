# How to Configure LLMWhisperer

This guide shows you how to configure the LLMWhisperer driver for document processing, including setting default options and overriding them on a per-document basis.

## Prerequisites

- Parxy installed with LLMWhisperer support: `pip install parxy[llmwhisperer]` or via UV `uv add parxy[llmwhisperer]`
- An LLMWhisperer API key from [Unstract](https://unstract.com/)

## Quick Start

### Step 1: Set Your API Key

Create a `.env` file in your project directory:

```bash
PARXY_LLMWHISPERER_API_KEY=your-api-key-here
```

Or set it as an environment variable:

```bash
export PARXY_LLMWHISPERER_API_KEY=your-api-key-here
```

### Step 2: Parse a Document

```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf", driver_name="llmwhisperer")
print(f"Processed {len(doc.pages)} pages")
```

## Configuration Options

LLMWhisperer supports configuration options that control parsing behavior. These can be set at two levels:

1. **Default configuration** - Applied to all documents via environment variables or config
2. **Per-call overrides** - Applied to specific documents via kwargs

### Environment Variables

All LLMWhisperer configuration uses environment variables with the `PARXY_LLMWHISPERER_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PARXY_LLMWHISPERER_API_KEY` | string | None | Your LLMWhisperer API key |
| `PARXY_LLMWHISPERER_BASE_URL` | string | `https://llmwhisperer-api.eu-west.unstract.com/api/v2` | API endpoint |
| `PARXY_LLMWHISPERER_LOGGING_LEVEL` | string | `INFO` | Client logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `PARXY_LLMWHISPERER_MODE` | string | `form` | Default parsing mode (see below) |

### Parsing Modes

LLMWhisperer offers several parsing modes with different accuracy and cost trade-offs:

- `native_text`: Extract native/copyable text only (fastest, cheapest)
- `low_cost`: Basic OCR extraction
- `high_quality`:High quality OCR with better accuracy
- `form`: Optimized for forms and structured documents (default)
- `table`: Optimized for documents with tables

## Per-Call Configuration Overrides

You can override the default parsing mode for specific documents by passing kwargs to `Parxy.parse()`:

```python
from parxy_core.facade.parxy import Parxy

# Use default configuration (form mode)
doc1 = Parxy.parse("simple.pdf", driver_name="llmwhisperer")

# Override mode for a specific document
doc2 = Parxy.parse(
    "scanned-document.pdf",
    driver_name="llmwhisperer",
    mode="high_quality",  # Use high quality OCR for scanned docs
)

# Use table mode for documents with many tables
doc3 = Parxy.parse(
    "financial-report.pdf",
    driver_name="llmwhisperer",
    mode="table",
)

# Use native text mode for simple PDFs with selectable text
doc4 = Parxy.parse(
    "digital-document.pdf",
    driver_name="llmwhisperer",
    mode="native_text",  # Fastest and cheapest
)
```

### Supported Per-Call Options

The following options can be overridden per-call:

- `mode` - Parsing mode (`native_text`, `low_cost`, `high_quality`, `form`, `table`)

## Use Cases

### Scanned Documents

For scanned documents that require OCR:

```python
doc = Parxy.parse(
    "scanned.pdf",
    driver_name="llmwhisperer",
    mode="high_quality",
)
```

### Forms and Structured Documents

For forms, applications, or structured documents:

```python
doc = Parxy.parse(
    "application-form.pdf",
    driver_name="llmwhisperer",
    mode="form",
)
```

### Documents with Tables

For spreadsheets, financial reports, or documents with complex tables:

```python
doc = Parxy.parse(
    "quarterly-report.pdf",
    driver_name="llmwhisperer",
    mode="table",
)
```

### Digital PDFs with Selectable Text

For PDFs created digitally (not scanned) where text is already selectable:

```python
doc = Parxy.parse(
    "digital-report.pdf",
    driver_name="llmwhisperer",
    mode="native_text",  # Skip OCR, extract text directly
)
```

### Cost-Optimized Processing

When processing many documents and cost is a concern:

```python
doc = Parxy.parse(
    "bulk-document.pdf",
    driver_name="llmwhisperer",
    mode="low_cost",
)
```

## Cost Estimation

Parxy automatically tracks parsing costs in the document metadata:

```python
doc = Parxy.parse("document.pdf", driver_name="llmwhisperer")

# Access cost information
metadata = doc.parsing_metadata
print(f"Estimated cost: {metadata.get('cost_estimation')} {metadata.get('cost_estimation_unit')}")
print(f"Parsing mode: {metadata.get('parsing_mode')}")
print(f"Pages processed: {metadata.get('pages_processed')}")
```

### Usage Information

LLMWhisperer also provides usage information from the API:

```python
doc = Parxy.parse("document.pdf", driver_name="llmwhisperer")

# Access usage information
usage_info = doc.parsing_metadata.get('usage_info')
if usage_info:
    print(f"Usage details: {usage_info}")
```

## Document Metadata

After parsing, the document contains additional metadata from LLMWhisperer:

```python
doc = Parxy.parse("document.pdf", driver_name="llmwhisperer")

metadata = doc.parsing_metadata

# Whisper-specific metadata
print(f"Whisper hash: {metadata.get('whisper_hash')}")

# Processing details
details = metadata.get('whisper_details', {})
print(f"Processing time: {details.get('processing_time_in_seconds')} seconds")
print(f"Total pages: {details.get('total_pages')}")
print(f"Processed pages: {details.get('processed_pages')}")
print(f"File size: {details.get('upload_file_size_in_kb')} KB")
```

## Troubleshooting

### Authentication Errors

If you see 401/403 errors:

1. Verify your API key is correct
2. Check the key has not expired
3. Ensure the key has access to the requested features


### Rate Limiting

If you encounter 429 errors (rate limiting):

1. Reduce the frequency of API calls
2. Implement retry logic with exponential backoff
3. Contact Unstract for higher rate limits if needed

### Quota Exceeded

If you see 402 errors (quota exceeded):

1. Check your account's remaining credits
2. Purchase additional credits from Unstract
3. Use lower-cost parsing modes for bulk processing

### Missing or Poor Quality Text

If text extraction is incomplete or low quality:

1. Use `high_quality` mode for better OCR accuracy
2. Try `form` mode for structured documents
3. Try `table` mode for documents with tables
4. Ensure the document is not corrupted

### Slow Processing

If parsing is slow:

1. Use `native_text` mode for digital PDFs (skips OCR)
2. Use `low_cost` mode for faster processing
3. Consider breaking large documents into smaller chunks

## Supported Extraction Levels

LLMWhisperer supports the following extraction levels:

- `page` - Page-level text extraction
- `block` - Block-level extraction (internally uses page-level)

Note: LLMWhisperer returns page-level text. When `block` level is requested, it internally uses `page` level as that is the native output format.

## See Also

- [LLMWhisperer Documentation](https://docs.unstract.com/llmwhisperer/)
- [LLMWhisperer Modes](https://docs.unstract.com/llmwhisperer/llm_whisperer/llm_whisperer_modes/)
- [Unstract Pricing](https://unstract.com/pricing/)
- [Getting Started Tutorial](../tutorials/getting_started.md)

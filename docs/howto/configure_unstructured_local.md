# How to Configure Unstructured Local

This guide shows you how to configure the Unstructured Local driver for document processing. This driver uses the open-source `unstructured` library for local document parsing without requiring external services.

## Prerequisites

- Parxy installed with Unstructured support: `pip install parxy[unstructured_local]` or via UV `uv add parxy[unstructured_local]`

## Quick Start

### Step 1: Install Dependencies

```bash
pip install parxy[unstructured_local]
```

Or with UV:

```bash
uv add parxy[unstructured_local]
```

### Step 2: Parse a Document

```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf", driver_name="unstructured_local")
print(f"Processed {len(doc.pages)} pages")
```

## Configuration Options

The Unstructured Local driver has minimal configuration since it runs locally. Environment variables use the `PARXY_UNSTRUCTURED_LOCAL_` prefix.

Currently, no specific configuration options are required. The driver uses sensible defaults from the `unstructured` library.

## Supported Extraction Levels

| Level | Description |
|-------|-------------|
| `page` | Extract text at page level only |
| `block` | Extract text as blocks with layout information |

```python
# Page-level extraction
doc = Parxy.parse("document.pdf", driver_name="unstructured_local", level="page")

# Block-level extraction (default)
doc = Parxy.parse("document.pdf", driver_name="unstructured_local", level="block")
```

## Input Types

The Unstructured Local driver accepts multiple input formats:

### Local Files

```python
doc = Parxy.parse("/path/to/document.pdf", driver_name="unstructured_local")
```

### BytesIO Streams

```python
import io

with open("document.pdf", "rb") as f:
    stream = io.BytesIO(f.read())

doc = Parxy.parse(stream, driver_name="unstructured_local")
```

### Raw Bytes

```python
with open("document.pdf", "rb") as f:
    data = f.read()

doc = Parxy.parse(data, driver_name="unstructured_local")
```

## Supported File Formats

The `unstructured` library supports many document formats:

- PDF (`.pdf`)
- Microsoft Word (`.docx`, `.doc`)
- PowerPoint (`.pptx`, `.ppt`)
- Excel (`.xlsx`, `.xls`)
- Plain Text (`.txt`)
- HTML (`.html`, `.htm`)
- Markdown (`.md`)
- Rich Text Format (`.rtf`)
- Email (`.eml`, `.msg`)
- Images (`.png`, `.jpg` - with OCR)

```python
# Process different file types
doc_pdf = Parxy.parse("report.pdf", driver_name="unstructured_local")
doc_word = Parxy.parse("document.docx", driver_name="unstructured_local")
doc_html = Parxy.parse("page.html", driver_name="unstructured_local")
```

## Element Categories

Unstructured identifies semantic categories for each text block:

```python
doc = Parxy.parse("document.pdf", driver_name="unstructured_local")

for page in doc.pages:
    for block in page.blocks:
        print(f"Category: {block.category}")
        print(f"Text: {block.text[:50]}...")
```

Common categories include:
- `Title` - Document or section titles
- `NarrativeText` - Body paragraphs
- `ListItem` - List items
- `Table` - Table content
- `Image` - Image elements
- `Header` - Page headers
- `Footer` - Page footers
- `FigureCaption` - Figure captions
- `Address` - Address blocks
- `EmailAddress` - Email addresses

## Bounding Box Information

Each text block includes coordinate information:

```python
doc = Parxy.parse("document.pdf", driver_name="unstructured_local")

for page in doc.pages:
    for block in page.blocks:
        if block.bbox:
            print(f"Block at: ({block.bbox.x0}, {block.bbox.y0})")
            print(f"Size: {block.bbox.x1} x {block.bbox.y1}")
```

## Language Detection

The driver detects document language automatically:

```python
doc = Parxy.parse("document.pdf", driver_name="unstructured_local")

print(f"Document language: {doc.language}")
```

## Source Data

Original Unstructured metadata is preserved:

```python
doc = Parxy.parse("document.pdf", driver_name="unstructured_local")

for page in doc.pages:
    for block in page.blocks:
        metadata = block.source_data
        print(f"Filename: {metadata.get('filename')}")
        print(f"Page: {metadata.get('page_number')}")
        print(f"Languages: {metadata.get('languages')}")
```

## Passing Options to Unstructured

You can pass additional options directly to the `unstructured` partitioner:

```python
doc = Parxy.parse(
    "document.pdf",
    driver_name="unstructured_local",
    # Options passed to unstructured.partition.auto.partition()
    strategy="hi_res",  # Use high-resolution strategy
    infer_table_structure=True,  # Extract table structure
    include_page_breaks=True,  # Include page break elements
)
```

### Common Options

| Option | Type | Description |
|--------|------|-------------|
| `strategy` | str | Partitioning strategy: `auto`, `fast`, `hi_res`, `ocr_only` |
| `infer_table_structure` | bool | Extract table structure as HTML |
| `include_page_breaks` | bool | Include page break elements |
| `languages` | list | Languages for OCR (e.g., `["eng", "deu"]`) |
| `ocr_languages` | str | Tesseract language codes |
| `encoding` | str | Text encoding for text files |

## Use Cases

### Multi-Format Processing

Process various document types uniformly:

```python
from pathlib import Path

documents = Path("docs/").glob("*.*")

for doc_path in documents:
    if doc_path.suffix.lower() in [".pdf", ".docx", ".html", ".txt"]:
        doc = Parxy.parse(str(doc_path), driver_name="unstructured_local")
        print(f"{doc_path.name}: {len(doc.pages)} pages")
```

### Content Classification

Classify content by element type:

```python
doc = Parxy.parse("document.pdf", driver_name="unstructured_local")

titles = []
body_text = []
lists = []

for page in doc.pages:
    for block in page.blocks:
        if block.category == "Title":
            titles.append(block.text)
        elif block.category == "NarrativeText":
            body_text.append(block.text)
        elif block.category == "ListItem":
            lists.append(block.text)

print(f"Titles: {len(titles)}")
print(f"Paragraphs: {len(body_text)}")
print(f"List items: {len(lists)}")
```

### Table Extraction

Extract tables with structure:

```python
doc = Parxy.parse(
    "document.pdf",
    driver_name="unstructured_local",
    infer_table_structure=True,
)

for page in doc.pages:
    for block in page.blocks:
        if block.category == "Table":
            # Table HTML is in source_data
            table_html = block.source_data.get("text_as_html")
            print(f"Table found: {block.text[:100]}...")
```

### Email Processing

Process email files:

```python
doc = Parxy.parse("message.eml", driver_name="unstructured_local")

for page in doc.pages:
    for block in page.blocks:
        print(f"[{block.category}] {block.text}")
```

### OCR Processing

Process scanned documents with OCR:

```python
doc = Parxy.parse(
    "scanned.pdf",
    driver_name="unstructured_local",
    strategy="ocr_only",
    languages=["eng"],
)

full_text = "\n".join(page.text for page in doc.pages)
print(full_text)
```

## Installation Options

The `unstructured` library has optional dependencies for different features:

```bash
# Basic installation (PDF, text, HTML)
pip install parxy[unstructured_local]

# With all document types
pip install "unstructured[all-docs]"

# With specific formats
pip install "unstructured[pdf,docx,pptx]"
```

### OCR Dependencies

For OCR support, install Tesseract:

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Comparison with Other Drivers

| Feature | Unstructured Local | PyMuPDF | PdfAct | LlamaParse |
|---------|-------------------|---------|--------|------------|
| Installation | Local | Local | Self-hosted | Cloud |
| Multi-format | Yes | PDF only | PDF only | PDF only |
| API Key | No | No | Optional | Required |
| Cost | Free | Free | Free | Per-page |
| Extraction Levels | 2 | 5 | 3 | 2 |
| Element Categories | Yes | No | Yes | Yes |
| OCR Support | Yes | Yes | No | Yes |
| Table Structure | Yes | No | No | Yes |

Choose Unstructured Local when:
- You need to process multiple document formats
- You want semantic element categorization
- You need OCR capabilities locally
- Privacy is important (local processing)
- You need table structure extraction

## Troubleshooting

### Import Errors

If you see import errors, ensure dependencies are installed:

```python
try:
    doc = Parxy.parse("document.pdf", driver_name="unstructured_local")
except ImportError as e:
    print("Install with: pip install parxy[unstructured_local]")
```

### File Not Found

```python
from parxy_core.exceptions import FileNotFoundException

try:
    doc = Parxy.parse("missing.pdf", driver_name="unstructured_local")
except FileNotFoundException as e:
    print(f"File not found: {e}")
```

### Parsing Errors

```python
from parxy_core.exceptions import ParsingException

try:
    doc = Parxy.parse("corrupted.pdf", driver_name="unstructured_local")
except ParsingException as e:
    print(f"Parsing failed: {e}")
```

### OCR Not Working

1. Verify Tesseract is installed: `tesseract --version`
2. Check language packs are available: `tesseract --list-langs`
3. Specify the correct language:

```python
doc = Parxy.parse(
    "scanned.pdf",
    driver_name="unstructured_local",
    languages=["eng"],  # Must match installed language pack
)
```

### Slow Processing

For faster processing of simple documents:

```python
doc = Parxy.parse(
    "document.pdf",
    driver_name="unstructured_local",
    strategy="fast",  # Skip expensive operations
)
```

### Memory Issues

For large documents, process in batches or use streaming:

```python
import gc

for pdf_path in large_pdf_list:
    doc = Parxy.parse(pdf_path, driver_name="unstructured_local")
    # Process document
    del doc
    gc.collect()
```

## See Also

- [Unstructured Documentation](https://docs.unstructured.io/)
- [Unstructured GitHub](https://github.com/Unstructured-IO/unstructured)
- [Getting Started Tutorial](../tutorials/getting_started.md)

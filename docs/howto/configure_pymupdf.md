# How to Configure PyMuPDF

This guide shows you how to use the PyMuPDF driver for document processing. PyMuPDF is the default driver in Parxy and requires no external services or API keys.

## Prerequisites

- Parxy installed (PyMuPDF is included in the base installation)

## Quick Start

PyMuPDF works out of the box with no configuration required:

```python
from parxy_core.facade.parxy import Parxy

# PyMuPDF is the default driver
doc = Parxy.parse("document.pdf")
print(f"Processed {len(doc.pages)} pages")

# Or explicitly specify the driver
doc = Parxy.parse("document.pdf", driver_name="pymupdf")
```

## Supported Extraction Levels

PyMuPDF supports the most comprehensive extraction hierarchy of all Parxy drivers:

| Level | Description | Includes |
|-------|-------------|----------|
| `page` | Page-level text only | Page text and dimensions |
| `block` | Text blocks | Pages + blocks with bounding boxes |
| `line` | Text lines | Pages + blocks + lines |
| `span` | Text spans | Pages + blocks + lines + spans with styling |
| `character` | Individual characters | Full hierarchy including each character |

```python
# Page-level extraction (fastest)
doc = Parxy.parse("document.pdf", level="page")

# Block-level extraction (default)
doc = Parxy.parse("document.pdf", level="block")

# Line-level extraction
doc = Parxy.parse("document.pdf", level="line")

# Span-level extraction (includes font styling)
doc = Parxy.parse("document.pdf", level="span")

# Character-level extraction (most detailed, slowest)
doc = Parxy.parse("document.pdf", level="character")
```

## Input Types

PyMuPDF accepts multiple input formats:

### Local Files

```python
doc = Parxy.parse("/path/to/document.pdf")
```

### BytesIO Streams

```python
import io

with open("document.pdf", "rb") as f:
    stream = io.BytesIO(f.read())

doc = Parxy.parse(stream, driver_name="pymupdf")
```

### Raw Bytes

```python
with open("document.pdf", "rb") as f:
    data = f.read()

doc = Parxy.parse(data, driver_name="pymupdf")
```

## Document Metadata

PyMuPDF extracts PDF metadata automatically:

```python
doc = Parxy.parse("document.pdf")

if doc.metadata:
    print(f"Title: {doc.metadata.title}")
    print(f"Author: {doc.metadata.author}")
    print(f"Subject: {doc.metadata.subject}")
    print(f"Keywords: {doc.metadata.keywords}")
    print(f"Creator: {doc.metadata.creator}")
    print(f"Producer: {doc.metadata.producer}")
    print(f"Created: {doc.metadata.created_at}")
    print(f"Modified: {doc.metadata.updated_at}")
```

## Style Information

At `span` level and above, PyMuPDF extracts rich styling information:

```python
doc = Parxy.parse("document.pdf", level="span")

for page in doc.pages:
    for block in page.blocks:
        for line in block.lines:
            for span in line.spans:
                if span.style:
                    print(f"Font: {span.style.font_name}")
                    print(f"Size: {span.style.font_size}")
                    print(f"Color: {span.style.color}")
                    print(f"Italic: {span.style.font_style == 'italic'}")
                    print(f"Bold: {span.style.weight == 400}")
                    print(f"Alpha: {span.style.alpha}")
```

## Bounding Box Information

All extraction levels include bounding box coordinates:

```python
doc = Parxy.parse("document.pdf", level="block")

for page in doc.pages:
    print(f"Page {page.number}: {page.width} x {page.height}")
    for block in page.blocks:
        if block.bbox:
            print(f"  Block: ({block.bbox.x0}, {block.bbox.y0}) to ({block.bbox.x1}, {block.bbox.y1})")
```

## Character-Level Extraction

For applications requiring precise character positioning (e.g., text overlay, redaction):

```python
doc = Parxy.parse("document.pdf", level="character")

for page in doc.pages:
    for block in page.blocks:
        for line in block.lines:
            for span in line.spans:
                for char in span.characters:
                    print(f"'{char.text}' at ({char.bbox.x0}, {char.bbox.y0})")
```

## Source Data

PyMuPDF preserves original data in the `source_data` field:

```python
doc = Parxy.parse("document.pdf", level="span")

for page in doc.pages:
    for block in page.blocks:
        # Block number from PyMuPDF
        print(f"Block number: {block.source_data.get('number')}")

        for line in block.lines:
            # Writing mode and direction
            print(f"Writing mode: {line.source_data.get('wmode')}")
            print(f"Direction: {line.source_data.get('dir')}")

            for span in line.spans:
                # Font flags, bidirectional info, metrics
                print(f"Flags: {span.source_data.get('flags')}")
                print(f"Ascender: {span.source_data.get('ascender')}")
                print(f"Descender: {span.source_data.get('descender')}")
```

## Parsing Warnings

PyMuPDF captures PDF parsing warnings:

```python
doc = Parxy.parse("document.pdf")

if doc.parsing_metadata and doc.parsing_metadata.get('warnings'):
    print(f"Warnings: {doc.parsing_metadata['warnings']}")
```

## Use Cases

### Text Extraction

Simple text extraction from a PDF:

```python
doc = Parxy.parse("document.pdf", level="page")

full_text = "\n\n".join(page.text for page in doc.pages)
print(full_text)
```

### Structured Content Analysis

Analyze document structure at block level:

```python
doc = Parxy.parse("document.pdf", level="block")

for page in doc.pages:
    print(f"\n=== Page {page.number} ===")
    for i, block in enumerate(page.blocks):
        print(f"Block {i}: {block.text[:50]}...")
```

### Font Analysis

Identify fonts used in a document:

```python
doc = Parxy.parse("document.pdf", level="span")

fonts = set()
for page in doc.pages:
    for block in page.blocks:
        for line in block.lines:
            for span in line.spans:
                if span.style and span.style.font_name:
                    fonts.add(span.style.font_name)

print(f"Fonts used: {fonts}")
```

### Text Position Mapping

Map text to coordinates for overlay or annotation:

```python
doc = Parxy.parse("document.pdf", level="line")

for page in doc.pages:
    for block in page.blocks:
        for line in block.lines:
            if "keyword" in line.text.lower():
                print(f"Found at page {page.number}: {line.bbox}")
```

### Highlighting Detection

Detect text styling patterns:

```python
doc = Parxy.parse("document.pdf", level="span")

bold_text = []
italic_text = []

for page in doc.pages:
    for block in page.blocks:
        for line in block.lines:
            for span in line.spans:
                if span.style:
                    if span.style.weight == 400:
                        bold_text.append(span.text)
                    if span.style.font_style == "italic":
                        italic_text.append(span.text)

print(f"Bold sections: {len(bold_text)}")
print(f"Italic sections: {len(italic_text)}")
```

## Performance Considerations

### Extraction Level Impact

Higher extraction levels require more processing:

| Level | Relative Speed | Memory Usage |
|-------|---------------|--------------|
| `page` | Fastest | Lowest |
| `block` | Fast | Low |
| `line` | Moderate | Moderate |
| `span` | Slower | Higher |
| `character` | Slowest | Highest |

Choose the minimum level needed for your use case.

### Large Documents

For large documents, consider processing page by page:

```python
import pymupdf

# Direct PyMuPDF access for memory efficiency
with pymupdf.open("large-document.pdf") as pdf:
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        text = page.get_text()
        # Process page text
        del text  # Free memory
```

## Comparison with Other Drivers

Choose PyMuPDF when:

- You need fast, local processing
- Privacy is important (no data leaves your system)
- You need detailed extraction (character-level)
- You need PDF metadata
- You want the simplest setup (no configuration)

## Troubleshooting

### File Not Found

```python
from parxy_core.exceptions import FileNotFoundException

try:
    doc = Parxy.parse("missing.pdf")
except FileNotFoundException as e:
    print(f"File not found: {e}")
```

### Corrupted PDFs

PyMuPDF handles many malformed PDFs gracefully. Check warnings:

```python
doc = Parxy.parse("possibly-corrupted.pdf")

if doc.parsing_metadata:
    warnings = doc.parsing_metadata.get('warnings', '')
    if warnings:
        print(f"PDF warnings: {warnings}")
```

### Empty Pages

Some PDFs contain image-only pages with no extractable text:

```python
doc = Parxy.parse("scanned-document.pdf")

for page in doc.pages:
    if not page.text.strip():
        print(f"Page {page.number} has no extractable text (may be scanned)")
```

For scanned documents, consider using LlamaParse or LLMWhisperer with OCR support.

### Memory Issues

For very large documents or batch processing:

```python
import gc

for pdf_path in pdf_files:
    doc = Parxy.parse(pdf_path)
    # Process document
    del doc
    gc.collect()  # Force garbage collection
```

## See Also

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Getting Started Tutorial](../tutorials/getting_started.md)
- [Document Model Reference](../reference/document_model.md)

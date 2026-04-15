---
title: Split PDFs
description: How to split a PDF into individual pages or page ranges, extract a subset into a new file.
---

# Split PDFs

This tutorial covers how to break a PDF apart using Parxy's Python API: splitting into individual pages, extracting a page range, splitting by chunks, and working with file attachments embedded in a PDF.

## What You'll Learn

By the end of this tutorial, you'll be able to:

- Split a PDF into one file per page
- Extract a contiguous page range into a single new PDF
- Split a PDF into fixed-size chunks

## Splitting into individual pages

`Parxy.pdf.split()` writes each page as a separate file inside an output directory:

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy

pages = Parxy.pdf.split(
    input_path=Path("document.pdf"),
    output_dir=Path("./pages"),
    prefix="doc"
)

for page_path in pages:
    print(f"Created: {page_path}")
# Created: pages/doc_page_1.pdf
# Created: pages/doc_page_2.pdf
# ...
```

### Splitting a specific page range

Page indices are 0-based. To split only a subset of the document:

```python
# Split pages 2–5 (0-based indices 1–4)
pages = Parxy.pdf.split(
    input_path=Path("document.pdf"),
    output_dir=Path("./pages"),
    prefix="doc",
    from_page=1,
    to_page=4,
)
# Creates: doc_page_2.pdf, doc_page_3.pdf, doc_page_4.pdf, doc_page_5.pdf
```

### Splitting into fixed-size chunks

To group pages into chunks of N rather than one file per page, use `PdfService.split_pdf_by_chunk()` directly:

```python
from pathlib import Path
from parxy_core.services.pdf_service import PdfService

output_dir = Path("./chunks")
output_dir.mkdir(exist_ok=True)

chunks = PdfService.split_pdf_by_chunk(
    input_path=Path("document.pdf"),
    output_dir=output_dir,
    prefix="chunk",
    chunk_size=10,  # 10 pages per file
)

for chunk_path in chunks:
    print(f"Created: {chunk_path}")
```

## Extracting pages into a single PDF

When you want a contiguous page range as one file rather than individual pages, use `PdfService.extract_pages()`:

```python
from pathlib import Path
from parxy_core.services.pdf_service import PdfService

# Extract pages 3–7 (0-based indices 2–6)
PdfService.extract_pages(
    input_path=Path("report.pdf"),
    output_path=Path("summary.pdf"),
    from_page=2,
    to_page=6,
)
```

Omit both page arguments to copy the whole document:

```python
PdfService.extract_pages(Path("original.pdf"), Path("copy.pdf"))
```

## Error handling

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy
from parxy_core.services.pdf_service import PdfService

# Invalid page range
try:
    Parxy.pdf.split(Path("doc.pdf"), Path("./out"), "doc", from_page=100)
except ValueError as e:
    print(f"Invalid page range: {e}")

# Missing attachment
with PdfService(Path("document.pdf")) as pdf:
    try:
        pdf.extract_attachment("nonexistent.txt")
    except KeyError as e:
        print(f"Attachment not found: {e}")

# PdfService used outside a context manager
pdf = PdfService(Path("document.pdf"))
try:
    pdf.list_attachments()
except RuntimeError as e:
    print(f"Context error: {e}")
```

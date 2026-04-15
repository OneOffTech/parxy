---
title: Merge PDFs
description: How to combine multiple PDF files into one using Parxy, with optional page ranges, and post-merge optimization.
---

# Merge PDFs

This tutorial covers how to combine multiple PDF files into a single document using Parxy's Python API, including page selection, file size optimization, and embedding attachments.

## What You'll Learn

By the end of this tutorial, you'll be able to:

- Merge multiple PDFs into a single file
- Select specific page ranges from each input file
- Reduce the file size of the merged output
- Embed data files as attachments in the final PDF

## Merging PDFs

The `Parxy.pdf.merge()` method combines multiple PDF files in the order they are provided.

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy

# Merge two complete PDFs
Parxy.pdf.merge(
    inputs=[
        (Path("chapter1.pdf"), None, None),  # All pages
        (Path("chapter2.pdf"), None, None),  # All pages
    ],
    output=Path("book.pdf")
)
```

Each entry in `inputs` is a tuple of `(path, from_page, to_page)`. Pass `None` for either page boundary to include up to the start or end of the file.

### Selecting page ranges

Pages use 0-based indexing. To include only a subset of pages from a file:

```python
Parxy.pdf.merge(
    inputs=[
        (Path("intro.pdf"), 0, 0),       # Only the first page
        (Path("content.pdf"), 0, 9),     # Pages 1–10
        (Path("appendix.pdf"), 4, None), # From page 5 to the end
    ],
    output=Path("selected.pdf")
)
```

## Optimizing the merged output

After merging, you can reduce file size with `Parxy.pdf.optimize()`:

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy

result = Parxy.pdf.optimize(
    input_path=Path("merged.pdf"),
    output_path=Path("merged_optimized.pdf")
)

print(f"Original:  {result['original_size']:,} bytes")
print(f"Optimized: {result['optimized_size']:,} bytes")
print(f"Reduction: {result['reduction_percent']:.1f}%")
```

Fine-tune the compression settings as needed:

```python
result = Parxy.pdf.optimize(
    input_path=Path("merged.pdf"),
    output_path=Path("merged_web.pdf"),
    scrub_metadata=True,       # Remove metadata and existing attachments
    subset_fonts=True,         # Keep only the font glyphs actually used
    compress_images=True,      # Enable image compression
    dpi_threshold=150,         # Only process images above 150 DPI
    dpi_target=72,             # Downsample to 72 DPI
    image_quality=60,          # JPEG quality (0–100)
    convert_to_grayscale=True  # Convert to grayscale
)
```

> Set `scrub_metadata=False` if you plan to add attachments after optimizing, as `scrub_metadata=True` removes any existing embedded files.

## Error handling

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy
from parxy_core.services.pdf_service import PdfService

# Missing input file
try:
    Parxy.pdf.merge([(Path("missing.pdf"), None, None)], Path("out.pdf"))
except FileNotFoundError as e:
    print(f"File not found: {e}")

# Invalid optimization parameter
try:
    Parxy.pdf.optimize(Path("doc.pdf"), Path("out.pdf"), image_quality=150)
except ValueError as e:
    print(f"Invalid parameter: {e}")

# Adding an attachment that already exists
with PdfService(Path("document.pdf")) as pdf:
    pdf.add_attachment(Path("data.csv"))
    try:
        pdf.add_attachment(Path("data.csv"))  # Duplicate name
    except ValueError as e:
        print(f"Attachment conflict: {e}")
```

## Next steps

- [Split PDFs](./split_pdf.md) — split a document into pages or page ranges
- [CLI reference: pdf:merge](../reference/cli.md#parxy-pdfmerge) — the same operations from the command line

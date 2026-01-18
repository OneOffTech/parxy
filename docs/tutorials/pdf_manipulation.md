# PDF Manipulation with Parxy

This tutorial covers how to manipulate PDF files programmatically using Parxy's Python API. You'll learn to merge, split, optimize PDFs, and manage file attachments.

## What You'll Learn

By the end of this tutorial, you'll be able to:

- Merge multiple PDFs into a single file
- Split a PDF into individual pages
- Optimize PDF file size with compression
- Add, list, extract, and remove PDF attachments
- Choose between the facade API and context manager patterns

## Two Ways to Manipulate PDFs

Parxy provides two complementary approaches for PDF manipulation:

| Approach | Best For | Pattern |
|----------|----------|---------|
| `Parxy.pdf` facade | Quick, one-off operations (merge, split, optimize) | Static methods |
| `PdfService` context manager | Working with a single PDF (attachments, modifications) | `with` statement |

## Part 1: Using the Parxy.pdf Facade

The `Parxy.pdf` namespace provides static methods for common PDF operations that don't require keeping a file open.

### Merging PDFs

Combine multiple PDF files into one:

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

You can also select specific page ranges (0-based indexing):

```python
# Merge specific pages from different PDFs
Parxy.pdf.merge(
    inputs=[
        (Path("intro.pdf"), 0, 0),      # Only first page
        (Path("content.pdf"), 0, 9),    # Pages 1-10
        (Path("appendix.pdf"), 4, None), # From page 5 to end
    ],
    output=Path("selected.pdf")
)
```

### Splitting PDFs

Split a PDF into individual page files:

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy

# Split into individual pages
pages = Parxy.pdf.split(
    input_path=Path("document.pdf"),
    output_dir=Path("./pages"),
    prefix="doc"
)

# Returns list of created files
for page_path in pages:
    print(f"Created: {page_path}")
# Output:
# Created: pages/doc_page_1.pdf
# Created: pages/doc_page_2.pdf
# ...
```

### Optimizing PDFs

Reduce PDF file size using compression techniques:

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy

# Basic optimization with defaults
result = Parxy.pdf.optimize(
    input_path=Path("large_scan.pdf"),
    output_path=Path("optimized.pdf")
)

print(f"Original: {result['original_size']:,} bytes")
print(f"Optimized: {result['optimized_size']:,} bytes")
print(f"Reduction: {result['reduction_percent']:.1f}%")
```

Fine-tune optimization settings:

```python
# Aggressive optimization for web delivery
result = Parxy.pdf.optimize(
    input_path=Path("presentation.pdf"),
    output_path=Path("web_ready.pdf"),
    scrub_metadata=True,       # Remove metadata and attachments
    subset_fonts=True,         # Keep only used font glyphs
    compress_images=True,      # Compress images
    dpi_threshold=150,         # Process images above 150 DPI
    dpi_target=72,             # Downsample to 72 DPI
    image_quality=60,          # JPEG quality (0-100)
    convert_to_grayscale=True  # Convert to grayscale
)
```

## Part 2: Using PdfService with Context Manager

For operations that require working with a PDF document (especially attachments), use the `PdfService` class with Python's context manager pattern.

### Opening a PDF

```python
from pathlib import Path
from parxy_core.services.pdf_service import PdfService

# Open PDF within context manager
with PdfService(Path("document.pdf")) as pdf:
    # Work with the PDF here
    attachments = pdf.list_attachments()
    print(f"Found {len(attachments)} attachments")

# PDF is automatically closed when exiting the block
```

> **Important**: Always use `PdfService` within a `with` statement. Operations outside the context manager will raise `RuntimeError`.

### Listing Attachments

```python
from pathlib import Path
from parxy_core.services.pdf_service import PdfService

with PdfService(Path("report.pdf")) as pdf:
    attachments = pdf.list_attachments()

    if not attachments:
        print("No attachments found")
    else:
        for name in attachments:
            info = pdf.get_attachment_info(name)
            print(f"- {name}")
            print(f"  Size: {info['size']:,} bytes")
            print(f"  Description: {info.get('description', 'N/A')}")
```

### Adding Attachments

```python
from pathlib import Path
from parxy_core.services.pdf_service import PdfService

with PdfService(Path("report.pdf")) as pdf:
    # Add a file with default name (uses filename)
    pdf.add_attachment(Path("data.csv"))

    # Add with custom name and description
    pdf.add_attachment(
        file_path=Path("analysis.xlsx"),
        name="quarterly_analysis.xlsx",
        desc="Q4 2024 Financial Analysis"
    )

    # Save the modified PDF
    pdf.save(Path("report_with_attachments.pdf"))
```

### Extracting Attachments

```python
from pathlib import Path
from parxy_core.services.pdf_service import PdfService

with PdfService(Path("package.pdf")) as pdf:
    # Extract a specific attachment
    content = pdf.extract_attachment("data.json")

    # Save to file
    output_path = Path("extracted_data.json")
    output_path.write_bytes(content)
    print(f"Extracted to {output_path}")
```

Extract all attachments:

```python
from pathlib import Path
from parxy_core.services.pdf_service import PdfService

output_dir = Path("./extracted")
output_dir.mkdir(exist_ok=True)

with PdfService(Path("archive.pdf")) as pdf:
    for name in pdf.list_attachments():
        content = pdf.extract_attachment(name)
        (output_dir / name).write_bytes(content)
        print(f"Extracted: {name}")
```

### Removing Attachments

```python
from pathlib import Path
from parxy_core.services.pdf_service import PdfService

with PdfService(Path("document.pdf")) as pdf:
    # Remove a specific attachment
    pdf.remove_attachment("old_data.csv")

    # Save changes
    pdf.save(Path("document_cleaned.pdf"))
```

## Complete Example: Document Processing Pipeline

Here's a practical example combining multiple operations:

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy
from parxy_core.services.pdf_service import PdfService


def process_report(input_dir: Path, output_path: Path):
    """Merge PDFs, attach source data, and optimize."""

    # Step 1: Find all PDFs to merge
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise ValueError(f"No PDFs found in {input_dir}")

    # Step 2: Merge all PDFs
    temp_merged = output_path.parent / "temp_merged.pdf"
    Parxy.pdf.merge(
        inputs=[(pdf, None, None) for pdf in pdf_files],
        output=temp_merged
    )
    print(f"Merged {len(pdf_files)} files")

    # Step 3: Add attachments with context manager
    with PdfService(temp_merged) as pdf:
        # Attach any CSV files from the input directory
        for csv_file in input_dir.glob("*.csv"):
            pdf.add_attachment(
                file_path=csv_file,
                desc=f"Source data: {csv_file.name}"
            )
            print(f"Attached: {csv_file.name}")

        # Save with attachments
        temp_with_attachments = output_path.parent / "temp_attached.pdf"
        pdf.save(temp_with_attachments)

    # Step 4: Optimize the final output
    result = Parxy.pdf.optimize(
        input_path=temp_with_attachments,
        output_path=output_path,
        scrub_metadata=False,  # Keep our attachments!
        compress_images=True
    )

    print(f"Final size: {result['optimized_size']:,} bytes")
    print(f"Saved to: {output_path}")

    # Cleanup temp files
    temp_merged.unlink()
    temp_with_attachments.unlink()


# Usage
process_report(
    input_dir=Path("./quarterly_reports"),
    output_path=Path("./output/Q4_2024_combined.pdf")
)
```

## Error Handling

Both APIs raise standard Python exceptions:

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy
from parxy_core.services.pdf_service import PdfService

# FileNotFoundError for missing files
try:
    Parxy.pdf.split(Path("missing.pdf"), Path("./out"), "doc")
except FileNotFoundError as e:
    print(f"File not found: {e}")

# ValueError for invalid parameters
try:
    Parxy.pdf.optimize(
        Path("doc.pdf"),
        Path("out.pdf"),
        image_quality=150  # Must be 0-100
    )
except ValueError as e:
    print(f"Invalid parameter: {e}")

# KeyError for missing attachments
with PdfService(Path("document.pdf")) as pdf:
    try:
        pdf.extract_attachment("nonexistent.txt")
    except KeyError as e:
        print(f"Attachment not found: {e}")

# RuntimeError for operations outside context manager
pdf = PdfService(Path("document.pdf"))
try:
    pdf.list_attachments()  # Not inside 'with' block!
except RuntimeError as e:
    print(f"Context error: {e}")
```

## Summary

In this tutorial you learned:

- **`Parxy.pdf.merge()`** - Combine multiple PDFs with optional page ranges
- **`Parxy.pdf.split()`** - Split a PDF into individual page files
- **`Parxy.pdf.optimize()`** - Reduce file size with compression options
- **`PdfService` context manager** - Work with attachments (add, list, extract, remove)

### When to Use Each Approach

| Use `Parxy.pdf` when... | Use `PdfService` when... |
|-------------------------|--------------------------|
| Merging multiple files | Adding/removing attachments |
| Splitting into pages | Extracting attachment content |
| Optimizing file size | Multiple operations on one file |
| One-shot operations | Need fine-grained control |

## Next Steps

- [PDF Manipulation from CLI](../howto/pdf_manipulation.md) - Command-line usage
- [Working with Attachments](working_with_attachments.md) - CLI attachment commands
- [Batch Processing](../howto/batch_processing.md) - Process multiple documents

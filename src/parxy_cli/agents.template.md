<parxy>
<!-- Parxy document processing instructions - managed by `parxy agents` command -->

## Parxy Document Processing

This project uses Parxy for document processing. Parxy is a document processing gateway that provides a unified text extraction interface across multiple services.

### Quick Start

```python
from parxy_core.facade.parxy import Parxy

# Using default driver (PyMuPDF)
doc = Parxy.parse("document.pdf")

# Using a specific driver
doc = Parxy.parse("document.pdf", driver_name="llamaparse")

# With extraction level
doc = Parxy.parse("document.pdf", level="span")
```

### Available Drivers

| Driver | Type | Installation | Best For |
|--------|------|--------------|----------|
| `pymupdf` | Local | Base install | Fast local processing, detailed extraction |
| `pdfact` | Self-hosted | Base install | Semantic roles, scientific papers |
| `llamaparse` | Cloud | `parxy[llama]` | Complex documents, OCR |
| `llmwhisperer` | Cloud | `parxy[llmwhisperer]` | Form extraction |
| `unstructured_local` | Local | `parxy[unstructured_local]` | Multi-format support |
| `landingai` | Cloud | `parxy[landingai]` | Vision-based extraction |

### Extraction Levels

The document model hierarchy: `page -> block -> line -> span -> character`

- `page`: Page-level text only (fastest)
- `block`: Text blocks with bounding boxes (default)
- `line`: Individual text lines
- `span`: Text spans with font styling
- `character`: Individual characters with positions

### Document Model

```python
doc = Parxy.parse("document.pdf", level="block")

# Access pages
for page in doc.pages:
    print(f"Page {page.number}: {page.width}x{page.height}")

    # Access blocks
    for block in page.blocks:
        print(f"  {block.role}: {block.text[:50]}...")

        # Bounding box
        if block.bbox:
            print(f"    Position: ({block.bbox.x0}, {block.bbox.y0})")
```

### CLI Commands

```bash
# Parse documents
parxy parse document.pdf
parxy parse document.pdf --driver llamaparse --level span

# Convert to markdown
parxy markdown document.pdf -o output/

# List available drivers
parxy drivers

# PDF manipulation
parxy pdf split document.pdf --pages 1-5
parxy pdf merge doc1.pdf doc2.pdf -o combined.pdf

# Manage attachments
parxy attach list document.pdf
parxy attach extract document.pdf -o attachments/
```

### Configuration

Environment variables use `PARXY_<DRIVER>_` prefix:

```bash
# LlamaParse
PARXY_LLAMAPARSE_API_KEY=llx-your-key

# PdfAct (self-hosted)
PARXY_PDFACT_BASE_URL=http://localhost:4567/

# LLMWhisperer
PARXY_LLMWHISPERER_API_KEY=your-key

# Observability
PARXY_TRACING_ENABLE=true
PARXY_TRACING_ENDPOINT=http://localhost:4318/
```

### Common Tasks

#### Extract Text from PDF

```python
from parxy_core.facade.parxy import Parxy

doc = Parxy.parse("document.pdf")
text = "\n\n".join(page.text for page in doc.pages)
```

#### Process with Specific Driver

```python
# Cloud processing with LlamaParse
doc = Parxy.parse(
    "complex-document.pdf",
    driver_name="llamaparse",
    parse_mode="parse_page_with_lvm",  # Vision model for tables
    continuous_mode=True,  # Multi-page tables
)
```

#### Batch Processing

```python
from pathlib import Path
from parxy_core.facade.parxy import Parxy

for pdf in Path("docs/").glob("*.pdf"):
    doc = Parxy.parse(str(pdf))
    print(f"{pdf.name}: {len(doc.pages)} pages")
```

#### Filter by Content Role

```python
doc = Parxy.parse("paper.pdf", driver_name="pdfact")

# Get only body text (skip headers/footers)
skip_roles = {"doc-pageheader", "doc-pagefooter", "doc-footnote"}
body_text = []

for page in doc.pages:
    for block in page.blocks:
        if block.role not in skip_roles:
            body_text.append(block.text)
```

### Error Handling

```python
from parxy_core.facade.parxy import Parxy
from parxy_core.exceptions import (
    FileNotFoundException,
    AuthenticationException,
    ParsingException,
)

try:
    doc = Parxy.parse("document.pdf", driver_name="llamaparse")
except FileNotFoundException:
    print("File not found")
except AuthenticationException:
    print("API key invalid or missing")
except ParsingException as e:
    print(f"Parsing failed: {e}")
```

### Development Commands

```bash
# Install all dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Format code
uv run ruff format

# Run CLI
uv run parxy parse document.pdf
```

### Documentation

For detailed guides, see the `docs/` directory:

- `docs/tutorials/` - Getting started, CLI usage
- `docs/howto/` - Driver configuration guides
- `docs/explanation/` - Architecture and concepts

### Key Files

When installed as a library in a virtual environment

- `.venv/Lib/site-packages/parxy_core/facade/parxy.py` - Main public API
- `.venv/Lib/site-packages/parxy_core/drivers/` - Driver implementations
- `.venv/Lib/site-packages/parxy_core/models/config.py` - Configuration classes
- `.venv/Lib/site-packages/parxy_core/models/models.py` - Document model

</parxy>

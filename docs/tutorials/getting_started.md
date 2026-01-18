# Getting Started with Parxy

Welcome to your first experience with **Parxy** — a unified Python interface for document parsing.  

This tutorial will guide you step-by-step through:

1. Parsing your first document with Parxy  
2. Loading a PDF and extracting its text  
3. Understanding the unified `Document` model returned by all parsers  

## What You'll Learn

By the end of this tutorial, you'll be able to:

- Install and use Parxy as a Python library  
- Parse documents with a single function call  
- Access structured text through Parxy's unified data model  
- Convert parsed documents to plain text or Markdown  

## Installation

Install Parxy from PyPI (or your development package):

```bash
pip install parxy
````

You can also install optional parser backends depending on your needs (e.g. PyMuPDF, Unstructured, LlamaParse):

```bash
pip install parxy[llama]
```


## Step 1 — Parse Your First Document

Let's start by parsing a simple PDF.

The easiest way is to use the `Parxy.parse()` method, which automatically selects the default parser (usually `pymupdf`).

```python
from parxy_core.facade.parxy import Parxy

# Parse a document from a local file path
doc = Parxy.parse("samples/example.pdf")

# Print basic information
print(f"Pages: {len(doc.pages)}")
print(f"Title: {doc.metadata.title}")
```

You can also specify a parser explicitly:

```python
doc = Parxy.parse("samples/example.pdf", driver_name=Parxy.PYMUPDF)
```

Or even pass an in-memory file:

```python
import io

with open("samples/example.pdf", "rb") as f:
    pdf_bytes = io.BytesIO(f.read())

doc = Parxy.parse(pdf_bytes)
```

> Each parser requires a configurations that can be specified through enviroment variables.
> Refers to [config.py](../../src/parxy_core/models/config.py) for details.


## Step 2 — Extract Text

Once parsed, the returned object is a [`Document`](../../src/parxy_core/models/models.py) model — a structured representation of your file.

You can access its text content in different ways:

**Get all text as a single string**

```python
text = doc.text()
print(text[:500])  # print first 500 characters
```

**Convert the document to Markdown**

```python
markdown = doc.markdown()
print(markdown[:500])
```

This method preserves headings, paragraphs, and lists (when identified by the parser).


## Step 3 — Explore the Unified Document Model

Every parser in Parxy returns the same structure, built with [Pydantic](https://docs.pydantic.dev/):

```
Document
 ├── Metadata
 ├── Page[]
 │   ├── TextBlock[]
 │   │   ├── Line[]
 │   │   │   ├── Span[]
 │   │   │   │   ├── Character[]
 │   │   │   │   └── ...
 │   ├── ImageBlock[]
 │   └── TableBlock[]
 └── Outline[]
```

Example:

```python
page = doc.pages[0]
first_block = page.blocks[0]

print(first_block.text)
print(first_block.bbox)
print(first_block.category)
```


## What Happens Under the Hood

When you call:

```python
doc = Parxy.parse("file.pdf")
```

Parxy performs the following steps:

1. Initializes a singleton `DriverFactory`
2. Selects the appropriate driver (e.g. PyMuPDF)
3. Invokes the driver's `.parse()` method
4. Returns a normalized `Document` object with consistent structure

This means **you can switch parsers** (e.g., from PyMuPDF to LlamaParse) without changing how you handle the output.

## Summary

In this tutorial you:

* Installed and imported Parxy
* Parsed a document with a single line of code
* Extracted text and Markdown
* Explored the unified document model

You're now ready to try more advanced use cases, such as:

* [Using Parxy from the command line](using_cli.md)
* [Processing multiple documents in parallel](../howto/batch_processing.md)
* Comparing different parsers on the same document
* [Extending Parxy with a custom driver](../howto/add_new_parser.md)
* [Monitoring document processing with OpenTelemetry](../howto/configure_observability.md)


> [!TIP]
> If your parsed text seems incomplete or misaligned, try a different driver:
>
> ```python
> doc = Parxy.parse("file.pdf", driver_name=Parxy.UNSTRUCTURED_LIBRARY)
> ```
>
> Each backend may specialize in different document types.

---
title: Introduction
description: What Parxy is, how it works, and a quick look at the CLI commands and Python library API before you dive in.
weight: 1
---

# Introduction

Parxy is a document processing gateway with a unified interface for multiple document parsing services. Via a common unified model it allows to swap providers without rewriting your application.

- Single API across different providers (local libraries and remote APIs)
- Supports PyMuPDF, Unstructured, LlamaParse, LLMWhisperer, PdfAct, and more
- Custom drivers can be registered directly in your application code
- Execution tracing to help debug parsing issues

## Available as CLI and library

Parxy works as a command line tool or as a Python library.

The quickest way to try it out is via [`uvx`](https://docs.astral.sh/uv/concepts/tools/#execution-vs-installation):

```bash
uvx parxy --help
```

To include all supported drivers:

```bash
uvx --from 'parxy[all]' parxy --help
```

See [Installation and Setup](./installation_and_setup.md) for the full installation options.

## CLI overview

Once installed, `parxy` provides the following commands:

| Command | Description |
|---------|-------------|
| `parxy parse` | Extract text content from documents with customizable granularity levels and output formats |
| `parxy markdown` | Convert documents into Markdown format, with optional combining of multiple documents |
| `parxy drivers` | List available document processing drivers |
| `parxy env` | Create a configuration file with default settings |
| `parxy docker` | Generate a Docker Compose configuration for self-hosted services |
| `parxy pdf:merge` | Merge multiple PDF files into one, with support for selecting specific page ranges |
| `parxy pdf:split` | Split a PDF file into individual pages |

```bash
# Parse a PDF to markdown
parxy parse --mode markdown document.pdf

# Launch interactive TUI for parser comparison
parxy tui ./documents

# Merge multiple PDFs with page ranges
parxy pdf:merge cover.pdf doc1.pdf[1:10] doc2.pdf -o merged.pdf
```

Run `parxy --help` for the full list of options.

## Library overview

Parxy can also be used directly in Python. After installation, import the `Parxy` facade:

```python
from parxy_core.facade import Parxy

# Parse a document using the default driver
doc = Parxy.parse('path/to/document.pdf')

print(f"Pages: {len(doc.pages)}")
print(f"Title: {doc.metadata.title}")

# Use a specific driver
doc = Parxy.driver(Parxy.LLAMAPARSE).parse('path/to/document.pdf')
```

Every driver returns the same `Document` structure, so you can switch providers without changing how you process the output.

For a step-by-step walkthrough, see the [Getting Started tutorial](./tutorials/getting_started.md).

## Next steps

- [Installation and first run](./installation_and_setup.md)
- [Available drivers](./supported_services.md) and their installation
- [Parse your first document](./tutorials/getting_started.md)

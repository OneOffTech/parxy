![pypi](https://img.shields.io/pypi/v/parxy.svg)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://docs.pydantic.dev/latest/contributing/#badges) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) [![CI](https://github.com/OneOffTech/parxy/actions/workflows/ci.yml/badge.svg)](https://github.com/OneOffTech/parxy/actions/workflows/ci.yml)

# OneOffTech Parxy

Parxy is a document processing gateway providing a unified interface to interact with multiple document parsing services, exposing a unified flexible document model suitable for different levels of text extraction granularity.

- Unified API to parse documents with different providers
- Unified flexible hierarchical document model (`page → block → line → span → character`)
- Supports both **local libraries** (e.g., PyMuPDF, Unstructured) and **remote services** (e.g., LlamaParse, LLMWhisperer, PdfAct)
- Extensible: easily integrate new parsers in your own code
- Trace the execution for debug purposes
- Pair with evaluation utilities to compare extraction results (coming soon)

**Requirements**

- Python 3.12 or above (Python 3.10 and 3.11 are supported on best-effort).


**Next steps**

- [Getting started](#getting-started)
    - [The Parxy CLI](#use-on-the-command-line)
    - [Install the library in your application](#use-as-a-library-in-your-project)
- [Supported document processing services](#supported-services)
- [Personalize drivers](#live-extension)

## Getting started

Parxy is available as a standalone command line and a library. The quickest way to try out Parxy is via command line using [`uvx`](https://docs.astral.sh/uv/concepts/tools/#execution-vs-installation).


Use with minimal footprint (fewer drivers supported):

```bash
uvx parxy --help
```

Use all supported drivers:

```bash
uvx parxy[all] --help
```

See [Supported services](#supported-services) for the list of included drivers and their extras for the installation.

### Use on the command line

You can install Parxy globally using either pip or uv. If you prefer you can execute without installation using [uvx](https://docs.astral.sh/uv/guides/tools/).

```bash
# Using pip
pip install parxy       # Basic installation
pip install parxy[all]  # All drivers included

# Using uv
uv pip install parxy       # Basic installation
uv pip install parxy[all]  # All drivers included

# Using uvx
uvx parxy       # Basic installation
uvx parxy[all]  # All drivers included
```

Once installed, you can use the `parxy` command to:

- `parxy tui`: Interactive TUI for comparing multiple parsers side-by-side with diff visualization
- `parxy parse`: Extract text content from documents with customizable granularity levels and output formats. Process individual files or entire folders, use multiple drivers, and control output with progress bars.
- `parxy preview`: Interactive document viewer showing metadata, table of contents, and content preview in a scrollable interface
- `parxy markdown`: Convert documents into Markdown format, with optional combining of multiple documents
- `parxy pdf:merge`: Merge multiple PDF files into one, with support for selecting specific page ranges
- `parxy pdf:split`: Split a PDF file into individual pages
- `parxy drivers`: List available document processing drivers
- `parxy env`: Create a configuration file with default settings
- `parxy docker`: Generate a Docker Compose configuration for self-hosted services

Example usage:

```bash
# Launch interactive TUI for parser comparison
parxy tui ./documents

# Parse a PDF to markdown
parxy parse --mode markdown document.pdf

# Parse entire folder with JSON output
parxy parse /path/to/pdfs -m json -o output/

# Parse with multiple drivers for comparison
parxy parse document.pdf -d pymupdf -d llamaparse

# Preview document interactively
parxy preview document.pdf

# Convert multiple PDFs to markdown and combine them
parxy markdown --combine -o output/ doc1.pdf doc2.pdf

# Merge multiple PDFs with page ranges
parxy pdf:merge cover.pdf doc1.pdf[1:10] doc2.pdf -o merged.pdf

# Split a PDF into individual pages
parxy pdf:split document.pdf -o ./pages

# List available drivers
parxy drivers
```

See [Using the Parxy Command Line Interface](./docs/tutorials/using_cli.md) or run `parxy --help` for more information about available commands and options.

### Use as a library in your project

1. Install, all or the driver you need

```bash
# Install all supported drivers via Pip
pip install parxy[all]

# add to your project using when using UV
uv add parxy[all]
```

You can also install [optional parser backends](#supported-services) depending on your needs (e.g. PyMuPDF, Unstructured, LlamaParse):

2. Add the env variables when needed

Some services require an api key. Parxy support those as environment variables. You can create a `.env` file in your project root.

```bash
# LlamaParse 
PARXY_LLAMAPARSE_API_KEY=

# Unstract LLMWhisperer
PARXY_LLMWHISPERER_API_KEY=
```

3. Call the driver


```python
from parxy_core.facade import Parxy

# Parse a document using the default driver
doc = Parxy.parse('path/to/document.pdf')

# Print basic information
print(f"Pages: {len(doc.pages)}")
print(f"Title: {doc.metadata.title}")

# Parse a document using a specific driver
Parxy.driver(Parxy.LLAMAPARSE).parse('path/to/document.pdf')
```

For more information take a look at our [Getting Started with Parxy tutorial](./docs/tutorials/getting_started.md).


## Supported services

| Service or Library | Support status | Extra | Local file | Remote file | 
|--------------------|----------------|-------|------------|-------------|
| [**PyMuPDF**](https://pymupdf.readthedocs.io/en/latest/) | Live | - | ✅ | ✅ |
| [**PdfAct**](https://github.com/data-house/pdfact) | Live | - | ✅ | ✅ |
| [**Unstructured** library](https://docs.unstructured.io/open-source/introduction/overview) | Preview | `unstructured_local` | ✅ | ✅ |
| [**Landing AI Agentic Document Extraction**](https://landing.ai/agentic-document-extraction) | Preview | `landingai` | ✅ | ✅ |
| [**LlamaParse**](https://docs.cloud.llamaindex.ai/llamaparse/overview) | Preview | `llama` | ✅ | ✅ |
| [**LLMWhisperer**](https://docs.unstract.com/llmwhisperer/index.html) | Preview | `llmwhisperer` | ✅ | ✅ |
| [**Unstructured.io** cloud service](https://docs.unstructured.io/open-source/introduction/overview) | Planned |  |  |  |
| [**Chunkr**](https://www.chunkr.ai/) | Planned |  |  |  |
| [**Docling**](https://docling-project.github.io/docling/) | Planned |  |  |  |


...and more can be added via the [live extension](#live-extension)!


### Live extension

Live Extension allow to add new drivers or create custom configuration of the current drivers directly in your app code.

1. Create a class that inherits from `Driver`

```python
from parxy_core.drivers import Driver
from parxy_core.models import Document

class CustomDriverExample(Driver):
    """Example custom driver for testing."""

    def _handle(self, file, level="page") -> Document:
        return Document(pages=[])
```

2. Register it in Parxy using the `extend` method

```python
Parxy.extend(name='my_parser', callback=lambda: CustomDriverExample())
```

3. Use it

```python
Parxy.driver('my_parser').parse('path/to/document.pdf')
```

More on the live extension in our [How to Add a New Parser to Parxy](./docs/howto/add_new_parser.md) guide.

## Contributing

Thank you for considering contributing to Parxy! You can find how to get started in our [contribution guide](./.github/CONTRIBUTING.md).

Interested in adding a new parser to the supported list, take a look at our [How to Add a New Parser to Parxy](./docs/howto/add_new_parser.md) guide.

### Development

Parxy uses [UV](https://docs.astral.sh/uv/) as package and project manager. 

1. Clone the repository
1. Sync all dependencies with `uv sync --all-extras`

All Parxy code is located in the `src` directory:

- `parxy_core` contains the drivers implementations, the models and the facade and factory to access Parxy features
- `parxy_cli` contains the module providing the command line interface


#### Optional Dependencies vs Dependency Groups

Parxy uses _optional dependencies_ to track user oriented dependencies that enhance functionality. Dependency groups are reserved for development purposes. When supporting a new driver consider defining it's dependencies as optional to reduce Parxy's footprint.

The question [What’s the difference between optional-dependencies and dependency-groups in pyproject.toml?](https://github.com/astral-sh/uv/issues/9011) give a nice overview of the differences.

### Testing

Parxy is tested using Pytest. Tests, located under `tests` folder, run for each commit and pull request.

To execute the test suite run:

```bash
uv run pytest
```

You can run type checking and linting via:

```bash
uv run ruff check
```


## Security Vulnerabilities

Please review our [security policy](./.github/SECURITY.md) on how to report security vulnerabilities.


## Supporters

The project is provided and supported by OneOff-Tech (UG) and Alessio Vertemati.

<p align="left"><a href="https://oneofftech.de" target="_blank"><img src="https://raw.githubusercontent.com/OneOffTech/.github/main/art/oneofftech-logo.svg" width="200"></a></p>


## Licence and Copyright

Parxy is licensed under the [GPL v3 licence](./LICENCE).

- Copyright (c) 2025-present Alessio Vertemati, @avvertix
- Copyright (c) 2025-present Oneoff-tech UG, www.oneofftech.de
- All contributors

[![CI](https://github.com/OneOffTech/parxy/actions/workflows/ci.yml/badge.svg)](https://github.com/OneOffTech/parxy/actions/workflows/ci.yml) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

# OneOffTech Parxy

Parxy is a document processing gateway providing a unified interface to interact with multiple document parsing services, exposing a unified flexible document model suitable for different levels of text extraction granularity.

- Unified API to parse documents with different providers
- Unified flexible hierarchical document model (`page → block → line → span → character`)
- Supports both **local libraries** (e.g., PyMuPDF, Unstructured) and **remote services** (e.g., LlamaParse, LLMWhisperer, PdfAct)
- Extensible: easily integrate new parsers in your own code
- Trace the execution for debug purposes
- Pair with evaluation utilities to compare extraction results (coming soon)

> [!NOTE]  
> Parxy is being rewritten from the ground up. Versions 0.6 and below are preserved in the legacy branch for historical purposes. The main branch contains the rewrite, which focuses on library and CLI usage. If you still need the HTTP API, continue using version 0.6.

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
uvx --from "git+https://github.com/oneofftech/parxy.git" parxy --help
```

Use all supported drivers:

```bash
uvx --from "git+https://github.com/oneofftech/parxy.git[all]" parxy --help
```

See [Supported services](#supported-services) for the list of included drivers and their extras for the installation.

### Use on the command line

_to be documented_

### Use as a library in your project

_to be documented_

1. Install, all or the driver you need

2. Add the env variables when needed

3. Call the driver


```python
from parxy_core.facade import Parxy

# Using the default driver, usually pymupdf
Parxy.parse('path/to/document.pdf')

# Using a specific driver
Parxy.driver(Parxy.LLAMAPARSE).parse('path/to/document.pdf')
```

## Supported services

| Service or Library | Support status | Extra | Local file | Remote file | 
|--------------------|----------------|-------|------------|-------------|
| [**PyMuPDF**](https://pymupdf.readthedocs.io/en/latest/) | Live | - | ✅ | ✅ |
| [**PdfAct**](https://github.com/data-house/pdfact) | Live | - | ✅ | ✅ |
| [**Unstructured** library](https://docs.unstructured.io/open-source/introduction/overview) | Preview | `unstructured_local` | ✅ | ✅ |
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

## Contributing

Thank you for considering contributing to Parxy! You can find how to get started in our [contribution guide](./.github/CONTRIBUTING.md).

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

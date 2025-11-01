# Copilot Instructions for Parxy

## Project Overview

Parxy is a document processing gateway providing a unified interface for text extraction from documents using multiple processing services. The project follows a driver-based architecture for extensibility.

### Core Concepts

- **Unified Document Model**: Hierarchical structure (`page → block → line → span → character`)
- **Driver System**: Abstract base + concrete implementations for different services
- **Configuration Management**: Environment-based with Pydantic models
- **Service Types**: Both local libraries (PyMuPDF, Unstructured) and remote services (LlamaParse, LLMWhisperer, PdfAct)

## Key Components

```
src/
  parxy_core/           # Core library implementation
    drivers/            # Document processing implementations
    facade/             # Main API interface (Parxy class)
    models/            # Data models and configuration
  parxy_cli/           # Command-line interface
```

### Important Patterns

1. **Driver Implementation**
   - Inherit from `Driver` base class in `drivers/abstract_driver.py`
   - Implement `_handle()` for parsing logic
   - Define `supported_levels` list
   - Use `_initialize_driver()` for setup
   - Example: See `drivers/pymupdf.py`

2. **Configuration Management**
   - Each driver has its own config class inheriting from `BaseConfig`
   - Environment variables prefixed with `parxy_`
   - Example: `models/config.py`

3. **Factory Pattern**
   - Central `DriverFactory` manages driver instantiation
   - Singleton pattern via `DriverFactory.build()`
   - Register custom drivers with `Parxy.extend()`

4. **Error Handling**
   - Custom exceptions in `exceptions/`
   - Drivers should raise appropriate exceptions (FileNotFound, Authentication, Parsing)

## Development Workflows

Project is in Python and uses [uv](https://docs.astral.sh/uv/) by Astral to manage virtual environments and dependencies.

All commands should be run with uv, e.g., `uv run <command>`.

1. **Testing**
   ```bash
   pytest tests/          # Run all tests
   pytest tests/drivers/  # Test specific driver
   ```

2. **Configuration**
   - Copy `.env.example` to `.env` for local settings
   - Use `parxy env` to generate default config

3. **Docker Integration**
   - `parxy docker` generates compose files for self-hosted services
   - See `compose.example.yaml` for reference

## Common Tasks

1. **Adding a New Driver**
   - Create new driver class in `drivers/`
   - Add config class in `models/config.py`
   - Register in `DriverFactory.get_supported_drivers()`
   - Add tests in `tests/drivers/`

2. **Testing File Processing**
   ```python
   from parxy_core.facade import Parxy
   
   # Using default driver (PyMuPDF)
   doc = Parxy.parse("document.pdf", level="block")
   
   # Specific driver
   doc = Parxy.parse("document.pdf", level="page", driver_name="llamaparse")
   ```

## Integration Points

1. **Remote Services**
   - LlamaParse: `api.cloud.eu.llamaindex.ai`
   - PdfAct: Self-hosted service
   - LLMWhisperer: Cloud service

2. **Local Dependencies**
   - PyMuPDF (fitz)
   - Unstructured
   - Python 3.12+ recommended
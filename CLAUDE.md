# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Parxy is a document processing gateway that provides a unified interface for extracting text from documents using multiple processing services (both local libraries and remote APIs). The core architecture is driver-based, where each service is implemented as a driver that converts its output to a unified hierarchical document model.

**Key Architecture**: `page → block → line → span → character` - This hierarchical model is fundamental to how Parxy works. All drivers normalize their output to this structure.

## Development Commands

### Environment Setup
```bash
# Sync all dependencies (including all optional drivers)
uv sync --all-extras

# Sync with specific driver only
uv sync --extra llama
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific driver tests
uv run pytest tests/drivers/test_pymupdf.py

# Run tests for a specific function
uv run pytest tests/drivers/test_pymupdf.py::test_function_name
```

### Code Quality
```bash
# Run linting
uv run ruff format

# Run type checking (implicit in Ruff)
uv run ruff check
```

### CLI Usage (for testing)
```bash
# Run CLI commands during development
uv run parxy parse document.pdf
uv run parxy drivers
uv run parxy markdown --combine -o output/ doc1.pdf doc2.pdf
```

## Core Architecture

### Driver System

**Base Class**: All drivers inherit from `Driver` (src/parxy_core/drivers/abstract_driver.py)

**Key patterns for implementing a driver**:
1. Inherit from `Driver` base class
2. Set `supported_levels` list (e.g., `['page', 'block', 'line', 'span', 'character']`)
3. Implement `_handle()` method that returns a `Document` object
4. Override `_initialize_driver()` if setup is needed
5. Create corresponding config class inheriting from `BaseConfig`

**Example driver structure** (see src/parxy_core/drivers/pymupdf.py:24-69):
```python
class NewDriver(Driver):
    supported_levels = ['page', 'block']

    def _initialize_driver(self):
        # Setup code if needed
        return self

    def _handle(self, file, level="block", **kwargs) -> Document:
        # Processing logic
        return Document(pages=[...])
```

### Configuration Management

- Each driver has a config class in `src/parxy_core/models/config.py`
- All config classes inherit from `BaseConfig` (Pydantic BaseSettings)
- Environment variables use `parxy_<drivername>_` prefix
- Example: `PARXY_LLAMAPARSE_API_KEY`, `PARXY_PDFACT_BASE_URL`
- Configuration is loaded from `.env` file automatically

### Factory Pattern

- `DriverFactory` (src/parxy_core/drivers/factory.py) manages driver instantiation
- Singleton pattern: Use `DriverFactory.build()` to get instance
- Drivers are created lazily on first use
- Custom drivers can be registered with `Parxy.extend(name, callback)`

### Public API (Facade)

The `Parxy` class (src/parxy_core/facade/parxy.py) provides the main public interface:
- `Parxy.parse(file, level, driver_name)` - Parse with specific or default driver
- `Parxy.driver(name)` - Get a driver instance
- `Parxy.extend(name, callback)` - Register custom driver
- Constants available: `Parxy.PYMUPDF`, `Parxy.LLAMAPARSE`, `Parxy.PDFACT`, etc.

## Key Components

### Source Structure
- `src/parxy_core/` - Core library implementation
  - `drivers/` - Driver implementations (pymupdf.py, llamaparse.py, pdfact.py, etc.)
  - `facade/` - Public API (`Parxy` class)
  - `models/` - Document models and configuration (models.py, config.py)
  - `exceptions/` - Custom exceptions
  - `logging/` - Logger setup
- `src/parxy_cli/` - CLI implementation
  - `commands/` - CLI command implementations
  - `models/` - CLI-specific models

### Document Model Hierarchy

Located in `src/parxy_core/models/models.py`:
- `Document` - Root containing pages and metadata
- `Page` - Contains blocks and page dimensions
- `TextBlock` / `ImageBlock` / `TableBlock` - Block types
- `Line` - Text lines within blocks
- `Span` - Text spans with style information
- `Character` - Individual characters with styling

All models are Pydantic BaseModels with optional bounding boxes and source_data fields.

### Extraction Levels

The `HierarchyLevel` enum defines supported granularity:
- `PAGE` - Page-level text only
- `BLOCK` - Page + blocks
- `LINE` - Page + blocks + lines
- `SPAN` - Page + blocks + lines + spans
- `CHARACTER` - Full hierarchy including individual characters

When processing at a specific level, only that level and above are populated in the result.

## Adding a New Driver

When implementing a new driver (see docs/howto/add_new_parser.md for full guide):

1. **Create driver class** in `src/parxy_core/drivers/newdriver.py`:
   - Inherit from `Driver`
   - Set `supported_levels`
   - Implement `_handle()` to return `Document`

2. **Create config class** in `src/parxy_core/models/config.py`:
   ```python
   class NewDriverConfig(BaseConfig):
       api_key: Optional[SecretStr] = None
       base_url: str = "https://api.example.com"

       model_config = SettingsConfigDict(
           env_prefix="parxy_newdriver_",
           env_file=".env",
           extra="ignore"
       )
   ```

3. **Register in factory** in `src/parxy_core/drivers/factory.py`:
   - Import the driver class
   - Add to `get_supported_drivers()` list
   - Add factory method `_create_newdriver_driver()`

4. **Add to public facade** in `src/parxy_core/facade/parxy.py`:
   - Add constant: `NEWDRIVER = 'newdriver'`

5. **Update pyproject.toml** if new dependencies needed:
   - Add as optional dependency with extra name

6. **Write tests** in `tests/drivers/test_newdriver.py`:
   - Test supported levels
   - Test authentication handling
   - Test output structure
   - Use fixtures from `tests/fixtures/`

## Exception Handling

Custom exceptions in `src/parxy_core/exceptions/`:
- `FileNotFoundException` - File/URL not accessible
- `AuthenticationException` - API authentication failed
- `ParsingException` - Processing errors
- `UnsupportedFormatException` - Invalid file types

Always use these instead of generic exceptions when implementing drivers.

## Optional Dependencies

Parxy uses optional dependencies to reduce footprint:
- Base install includes only PyMuPDF and PdfAct
- `parxy[llama]` - LlamaParse support
- `parxy[llmwhisperer]` - LLMWhisperer support
- `parxy[unstructured_local]` - Unstructured library support
- `parxy[all]` - All drivers

When adding new drivers, define dependencies as optional in pyproject.toml.

## Testing Strategy

- Driver tests in `tests/drivers/` verify:
  - Supported extraction levels work correctly
  - Authentication is handled properly
  - Error conditions raise appropriate exceptions
  - Output conforms to `Document` model
- Test fixtures stored in `tests/fixtures/`
- Use `pytest -v` for verbose output
- Integration tests in `tests/` root verify full pipeline

## Environment Variables

Core configuration (prefix: `parxy_`):
- `PARXY_DEFAULT_DRIVER` - Default driver name (default: 'pymupdf')
- `PARXY_LOGGING_LEVEL` - Logging level (default: INFO)
- `PARXY_LOGGING_FILE` - Log file path (default: None)

Driver-specific (see config.py for each driver):
- `PARXY_LLAMAPARSE_API_KEY`
- `PARXY_LLMWHISPERER_API_KEY`
- `PARXY_PDFACT_BASE_URL`
- etc.

## Important Implementation Notes

1. **File Input Handling**: Drivers must accept `str | io.BytesIO | bytes`:
   - `str` can be file path or URL (use `validators.url()` to check)
   - Use `Driver.get_stream_from_url()` for URL downloads
   - Convert paths to streams as needed by the underlying library

2. **Level Validation**: Always call `self._validate_level(level)` before processing

3. **Logging**: Use `self._logger` (passed to driver automatically)

4. **Configuration**: Access via `self._config` in driver implementation

5. **PyMuPDF Warnings**: Collect warnings and add to `parsing_metadata` (see pymupdf.py:64)

6. **Hierarchy Levels**: Use `HierarchyLevel` enum to conditionally populate model fields based on requested level (see pymupdf.py:200-206)

7. **Use Pathlib**: Use Pathlib instead of os.path for filesystem interaction

## Build System

- Uses `uv` as build backend (uv_build)
- Two modules built: `parxy_core` and `parxy_cli`
- Entry point: `parxy` command maps to `parxy_cli.cli:main`

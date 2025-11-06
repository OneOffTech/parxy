# Parxy AI Agent Guide

Welcome, AI Assistant! This guide will help you understand and work with the Parxy codebase effectively.

## Project Purpose

Parxy is a document processing gateway that provides:

- Unified text extraction interface across multiple services
- Consistent document model for all processing results
- Easy integration of new document processing services
- Support for both local and remote processing options

## Key Architectural Decisions

1. **Driver Architecture**
   - Each text extraction service is implemented as a driver
   - All drivers inherit from `Driver` base class
   - Configuration managed through environment variables via Pydantic models defined in `src/parxy_core/models/config.py`
   - Common interface regardless of underlying service

2. **Document Model**
   - Hierarchical structure: `page → block → line → span → character`
   - Each level provides increasing text granularity
   - Drivers declare supported extraction levels
   - Results normalized to this structure regardless of source

## Main Components

1. **Core Library (`parxy_core/`)**
   - `drivers/`: Service implementations
   - `facade/`: Public API (`Parxy` class)
   - `models/`: Data structures and config
   - `exceptions/`: Error handling
   - `logging/`: Debug support

2. **CLI Tool (`parxy_cli/`)**
   - Document processing commands
   - Configuration management
   - Docker environment setup

## Working with the Code

### Key Files to Understand

- `drivers/abstract_driver.py`: Base driver interface
- `models/config.py`: Configuration system
- `facade/parxy.py`: Main public API
- `drivers/factory.py`: Driver instantiation logic

### Common Code Patterns

1. **Driver Implementation**
   ```python
   class NewDriver(Driver):
       supported_levels = ["page", "block"]
       
       def _initialize_driver(self):
           # Setup code
           
       def _handle(self, file, level="block", **kwargs):
           # Processing logic
           return Document(...)
   ```

2. **Configuration**
   ```python
   class NewDriverConfig(BaseConfig):
       api_key: SecretStr
       base_url: str = "https://api.example.com"
       
       model_config = SettingsConfigDict(
           env_prefix="parxy_newdriver_"
       )
   ```
### Common Code Guidelines

- Prefer Pathlib over os.path


### Error Handling

Always use appropriate exceptions:
- `FileNotFoundException`: Missing or inaccessible files
- `AuthenticationException`: API auth issues
- `ParsingException`: Processing errors
- `UnsupportedFormatException`: Invalid file types

## Testing Strategy

1. Driver tests should:
   - Verify supported extraction levels
   - Test authentication handling
   - Check error conditions
   - Validate output structure
   - Use fixtures in `tests/fixtures/`

2. Integration tests should:
   - Test full processing pipeline
   - Verify configuration loading
   - Check driver factory patterns
   - Validate CLI functionality

## Environment Setup

1. **Local Development**
   ```bash
   uv sync --all-extras
   ```

2. **Configuration**
   - Copy `.env.example` to `.env`
   - Configure required services
   - Set logging as needed

## Need Help?

1. Check `docs/` directory:
   - `howto/`: Implementation guides
   - `tutorials/`: Usage examples

2. Review test files for:
   - Usage patterns
   - Edge cases
   - Configuration examples
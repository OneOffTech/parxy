from typing import Optional

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class ParxyConfig(BaseSettings):
    """Configuration values for Parxy. All env variables must start with parxy_"""

    default_driver: Optional[str] = 'pymupdf'
    """The default driver to use in case nothing is specified. Default 'pymupdf'."""

    logging_level: Optional[int] = logging.INFO
    """The logging level. Default "logging.INFO"."""

    logging_file: Optional[str] = None
    """The log file path. Specify to save logs to file. Default "None"."""

    tracing_enabled: Optional[bool] = False
    """Set to true to enable saving raw document processing drivers output to file. Default false."""

    tracing_directory: Optional[str] = 'storage/traces'
    """The directory to save trace files. Default "storage/traces"."""

    model_config = SettingsConfigDict(
        env_prefix='parxy_', env_file='.env', extra='ignore'
    )


class PdfActConfig(BaseSettings):
    """Configuration values for PdfAct service. All env variables must start with parxy_pdfact_"""

    base_url: str = 'http://localhost:4567/'
    """The base URL of the PdfAct API."""

    api_key: Optional[str] = None
    """The authentication key."""

    model_config = SettingsConfigDict(
        env_prefix='parxy_pdfact_', env_file='.env', extra='ignore'
    )


class LlamaParseConfig(BaseSettings):
    """Configuration values for LlamaParse service. All env variables must start with parxy_llamaparse_"""

    base_url: str = 'https://api.cloud.eu.llamaindex.ai'
    """The base URL of the Llama Parsing API."""

    api_key: str = None
    """The authentication key"""

    organization_id: Optional[str] = None
    """The organization ID for the LlamaParse API."""

    project_id: Optional[str] = None
    """The project ID for the LlamaParse API."""

    num_workers: Optional[int] = 4
    """The number of workers to use sending API requests for parsing."""

    show_progress: Optional[bool] = False
    """Show progress when parsing multiple files."""

    verbose: Optional[bool] = False
    """Whether to print the progress of the parsing."""

    # Parsing specific configurations (Alphabetical order)

    disable_ocr: Optional[bool] = False
    """Disable the OCR on the document. LlamaParse will only extract the copyable text from the document."""

    disable_image_extraction: Optional[bool] = False
    """If set to true, the parser will not extract images from the document. Make the parser faster."""

    do_not_cache: Optional[bool] = True
    """If set to true, the document will not be cached. This mean that you will be re-charged it you reprocess them as they will not be cached."""

    model_config = SettingsConfigDict(
        env_prefix='parxy_llamaparse_', env_file='.env', extra='ignore'
    )


class LlmWhispererConfig(BaseSettings):
    """Configuration values for LlmWhisperer service. All env variables must start with `parxy_llmwhisperer_`"""

    base_url: str = 'https://llmwhisperer-api.eu-west.unstract.com/api/v2'
    """The base URL of the LlmWhisperer API v2."""

    api_key: Optional[str] = None
    """The authentication key."""

    logging_level: Optional[str] = 'INFO'
    """The logging level for the client. Can be "DEBUG", "INFO", "WARNING" or "ERROR". Default "INFO"."""

    model_config = SettingsConfigDict(
        env_prefix='parxy_llmwhisperer_', env_file='.env', extra='ignore'
    )


class UnstructuredLocalConfig(BaseSettings):
    """Configuration values for Unstructured library. All env variables must start with `parxy_unstructured_local_`"""

    model_config = SettingsConfigDict(
        env_prefix='parxy_unstructured_local_', env_file='.env', extra='ignore'
    )

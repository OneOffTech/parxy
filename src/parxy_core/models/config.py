from typing import Literal, Optional

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import Field, SecretStr, BaseModel


class BaseConfig(BaseSettings):
    """Base class for configuration values."""

    pass


class ParxyTracingConfig(BaseSettings):
    """Configuration values for Parxy Observability based on Open Telemetry. All env variables must start with parxy_tracing_"""

    enable: bool = False
    """Enable sending traces to the observability service. Default False."""

    api_key: Optional[SecretStr] = Field(exclude=True, default=None)
    """The authentication key (used for both traces and metrics unless overridden)."""

    endpoint: str = 'http://localhost:4318/'
    """The base url of the Open Telemetry collector endpoint."""

    enable_metrics: bool = False
    """Enable sending metrics to the telemetry service. Default False."""

    traces_endpoint: str = Field(
        default_factory=lambda data: f'{data["endpoint"].rstrip("/")}/v1/traces'
    )
    """The endpoint for the traces exporter. Default 'http://localhost:4318/v1/traces'."""

    metrics_endpoint: str = Field(
        default_factory=lambda data: f'{data["endpoint"].rstrip("/")}/v1/metrics'
    )
    """The endpoint for the metrics exporter. Default 'http://localhost:4318/v1/metrics'."""

    timeout_seconds: int = 10
    """The client timeout when sending traces. Default 10 seconds."""

    use_compression: bool = True
    """The client should compress traces before send. Default True."""

    # metrics_export_interval_millis : Optional[int] = None,  # Export every 60 seconds
    # """The interval at which exporting metrics."""

    verbose: bool = True
    """Log when traces are sent. Useful for CLI to show telemetry activity. Default True."""

    authentication_header: str = 'Authorization'
    """The header in which the api key needs to be included for authentication purposes."""

    model_config = SettingsConfigDict(
        env_prefix='parxy_tracing_',
        env_file='.env',
        extra='ignore',
        nested_model_default_partial_update=True,
    )


class ParxyConfig(BaseConfig):
    """Configuration values for Parxy. All env variables must start with parxy_"""

    default_driver: Optional[str] = 'pymupdf'
    """The default driver to use in case nothing is specified. Default 'pymupdf'."""

    logging_level: Optional[int] = logging.INFO
    """The logging level. Default "logging.INFO"."""

    logging_file: Optional[str] = None
    """The log file path. Specify to save logs to file. Default "None"."""

    theme: Optional[Literal['light', 'dark']] = None
    """The console theme to use. Set to 'light' for light terminals or 'dark' for dark terminals. Default None (auto-detect)."""

    tracing: ParxyTracingConfig = ParxyTracingConfig()
    """Tracing configuration"""

    model_config = SettingsConfigDict(
        env_prefix='parxy_',
        env_file='.env',
        extra='ignore',
        nested_model_default_partial_update=True,
    )


class PdfActConfig(BaseConfig):
    """Configuration values for PdfAct service. All env variables must start with parxy_pdfact_"""

    base_url: str = 'http://localhost:4567/'
    """The base URL of the PdfAct API."""

    api_key: Optional[SecretStr] = Field(exclude=True, default=None)
    """The authentication key."""

    model_config = SettingsConfigDict(
        env_prefix='parxy_pdfact_', env_file='.env', extra='ignore'
    )


class LandingAIConfig(BaseConfig):
    """Configuration values for LandingAI service. All env variables must start with parxy_landingai_"""

    api_key: Optional[SecretStr] = Field(exclude=True, default=None)
    """The authentication key."""

    environment: Literal['production', 'eu'] | None = 'eu'
    """The environment to use. Production generally means https://api.va.landing.ai, while eu points to https://api.va.eu-west-1.landing.ai"""

    base_url: Optional[str] = None
    """The base URL of the Landing AI ADE API. When setting a custom base URL ensure environment is set to None"""

    model_config = SettingsConfigDict(
        env_prefix='parxy_landingai_', env_file='.env', extra='ignore'
    )


class LlamaParseConfig(BaseConfig):
    """Configuration values for LlamaParse service. All env variables must start with parxy_llamaparse_"""

    # Connection settings
    base_url: str = 'https://api.cloud.eu.llamaindex.ai'
    """The base URL of the Llama Parsing API."""

    api_key: SecretStr = Field(exclude=True, default=None)
    """The authentication key"""

    organization_id: Optional[str] = None
    """The organization ID for the LlamaParse API."""

    project_id: Optional[str] = None
    """The project ID for the LlamaParse API."""

    # Client behavior
    num_workers: Optional[int] = 4
    """The number of workers to use sending API requests for parsing."""

    show_progress: Optional[bool] = False
    """Show progress when parsing multiple files."""

    verbose: Optional[bool] = False
    """Whether to print the progress of the parsing."""

    # Parsing mode configuration
    parse_mode: Optional[str] = 'parse_page_with_llm'
    """Parsing mode to use. Options: 'accurate', 'parse_page_without_llm', 'parse_page_with_llm', 'parse_page_with_lvm', 'parse_page_with_agent', 'parse_document_with_llm', 'parse_document_with_agent'."""

    preset: Optional[str] = None
    """Parser preset. If set, overrides most other parameters. See LlamaParse documentation for available presets."""

    model: Optional[str] = None
    """Document model name for parse_with_agent mode."""

    premium_mode: Optional[bool] = False
    """Use best parser mode if set to True."""

    fast_mode: Optional[bool] = False
    """Use faster mode that skips OCR of images and table/heading reconstruction. Not compatible with gpt-4o."""

    # OCR and extraction settings
    disable_ocr: Optional[bool] = False
    """Disable the OCR on the document. LlamaParse will only extract the copyable text from the document."""

    disable_image_extraction: Optional[bool] = False
    """If set to true, the parser will not extract images from the document. Makes the parser faster."""

    high_res_ocr: Optional[bool] = False
    """Use high resolution OCR to extract text from images. Increases accuracy but reduces speed."""

    extract_layout: Optional[bool] = False
    """Extract layout information from the document. Costs 1 credit per page."""

    # Text handling
    skip_diagonal_text: Optional[bool] = False
    """Skip diagonal text (when text rotation in degrees modulo 90 is not 0). Useful for CAD drawings."""

    language: Optional[str] = 'en'
    """Language of the text to parse."""

    do_not_unroll_columns: Optional[bool] = False
    """Keep columns in text according to document layout. May reduce reconstruction accuracy."""

    # Page selection
    target_pages: Optional[str] = None
    """Target pages to extract. Comma-separated list of page numbers (0-indexed). E.g., '0,2,5-10'."""

    max_pages: Optional[int] = None
    """Maximum number of pages to extract. If not set, all pages are extracted."""

    # Advanced features
    continuous_mode: Optional[bool] = False
    """Parse documents continuously for better results on tables spanning multiple pages."""

    auto_mode: Optional[bool] = False
    """Automatically select best mode based on page content. Upgrades matching pages to Premium mode."""

    # Caching
    do_not_cache: Optional[bool] = True
    """If set to true, the document will not be cached. You will be re-charged if you reprocess them."""

    model_config = SettingsConfigDict(
        env_prefix='parxy_llamaparse_', env_file='.env', extra='ignore'
    )


class LlmWhispererConfig(BaseConfig):
    """Configuration values for LlmWhisperer service. All env variables must start with `parxy_llmwhisperer_`"""

    base_url: str = 'https://llmwhisperer-api.eu-west.unstract.com/api/v2'
    """The base URL of the LlmWhisperer API v2."""

    api_key: Optional[SecretStr] = Field(exclude=True, default=None)
    """The authentication key."""

    logging_level: Optional[str] = 'INFO'
    """The logging level for the client. Can be "DEBUG", "INFO", "WARNING" or "ERROR". Default "INFO"."""

    mode: Optional[str] = 'form'
    """Default parsing mode. Can be high_quality, form, low_cost or native_text"""

    model_config = SettingsConfigDict(
        env_prefix='parxy_llmwhisperer_', env_file='.env', extra='ignore'
    )


class UnstructuredLocalConfig(BaseConfig):
    """Configuration values for Unstructured library. All env variables must start with `parxy_unstructured_local_`"""

    model_config = SettingsConfigDict(
        env_prefix='parxy_unstructured_local_', env_file='.env', extra='ignore'
    )

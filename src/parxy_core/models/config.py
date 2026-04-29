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
    """The base URL of the LlamaParse API. Override to use a different region or self-hosted instance."""

    api_key: SecretStr = Field(exclude=True, default=None)
    """The authentication key."""

    organization_id: Optional[str] = None
    """The organization ID for the LlamaParse API."""

    project_id: Optional[str] = None
    """The project ID for the LlamaParse API."""

    # Parsing tier (LlamaParse API v2)
    tier: Optional[Literal['fast', 'cost_effective', 'agentic', 'agentic_plus']] = None
    """Parsing tier to use. Options: 'fast' (rule-based, cheapest), 'cost_effective' (balanced),
    'agentic' (AI-powered), 'agentic_plus' (premium AI). Defaults to 'cost_effective' when not set."""

    version: Optional[str] = 'latest'
    """API version string. Use 'latest' for the current stable version or a date string for reproducibility."""

    # Legacy parsing mode (LlamaParse API v1, mapped to tier for backward compatibility)
    parse_mode: Optional[str] = None
    """Legacy parsing mode. Mapped to the equivalent tier automatically.
    Options: 'parse_page_without_llm' → fast, 'parse_page_with_llm' / 'accurate' → cost_effective,
    'parse_page_with_lvm' / 'parse_page_with_agent' / 'parse_document_with_llm' → agentic,
    'parse_document_with_agent' → agentic_plus."""

    premium_mode: Optional[bool] = False
    """If True, selects the 'agentic_plus' tier (legacy shorthand)."""

    fast_mode: Optional[bool] = False
    """If True, selects the 'fast' tier (legacy shorthand)."""

    # OCR and text extraction
    disable_ocr: Optional[bool] = False
    """Disable OCR on images embedded in the document."""

    skip_diagonal_text: Optional[bool] = False
    """Skip text rotated at an angle (e.g. watermarks, CAD annotations)."""

    language: Optional[str] = 'en'
    """Primary language for OCR (e.g. 'en', 'de', 'fr')."""

    # Output options
    do_not_unroll_columns: Optional[bool] = False
    """Keep multi-column layout intact instead of linearising columns into sequential text."""

    disable_image_extraction: Optional[bool] = False
    """If True, skip image extraction. Makes parsing faster."""

    continuous_mode: Optional[bool] = False
    """Automatically merge tables that span multiple pages."""

    # Page selection
    target_pages: Optional[str] = None
    """Specific pages to extract. Comma-separated 1-based page numbers or ranges (e.g. '1,3,5-8')."""

    max_pages: Optional[int] = None
    """Maximum number of pages to extract. Extracts all pages when not set."""

    # Caching
    do_not_cache: Optional[bool] = True
    """If True, bypass result caching and force re-parsing."""

    # Client behavior
    verbose: Optional[bool] = False
    """Print progress indicators during parsing."""

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

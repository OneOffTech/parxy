---
title: Configuration reference
description: Configuration options for Parxy and the drivers. Settings are read from the environment or a .env file. Run parxy env to generate a starter .env with some default.
---

<!-- This file is auto-generated from the source code. Do not edit it manually. -->
<!-- Regenerate with: python scripts/generate_docs.py -->

# Configuration reference

All settings are read from environment variables or a `.env` file in your project root.

Run `parxy env` to generate a template `.env` with usual configuration options.

## Core settings

Prefix: `PARXY_`

| Variable | Default | Description |
|----------|---------|-------------|
| `PARXY_DEFAULT_DRIVER` | `pymupdf` | The default driver to use in case nothing is specified. |
| `PARXY_LOGGING_LEVEL` | `INFO` | The logging level. |
| `PARXY_LOGGING_FILE` | - | The log file path. |
| `PARXY_THEME` | - | The console theme to use. One of: `light`, `dark`. |

## Observability / tracing

Prefix: `PARXY_TRACING_`

| Variable | Default | Description |
|----------|---------|-------------|
| `PARXY_TRACING_ENABLE` | `false` | Enable sending traces to the observability service. |
| `PARXY_TRACING_API_KEY` | *(secret)* | The authentication key (used for both traces and metrics unless overridden). |
| `PARXY_TRACING_ENDPOINT` | `http://localhost:4318/` | The base url of the Open Telemetry collector endpoint. |
| `PARXY_TRACING_ENABLE_METRICS` | `false` | Enable sending metrics to the telemetry service. |
| `PARXY_TRACING_TRACES_ENDPOINT` | *(computed)* | The endpoint for the traces exporter. |
| `PARXY_TRACING_METRICS_ENDPOINT` | *(computed)* | The endpoint for the metrics exporter. |
| `PARXY_TRACING_TIMEOUT_SECONDS` | `10` | The client timeout when sending traces. |
| `PARXY_TRACING_USE_COMPRESSION` | `true` | The client should compress traces before send. |
| `PARXY_TRACING_VERBOSE` | `true` | Log when traces are sent. |
| `PARXY_TRACING_AUTHENTICATION_HEADER` | `Authorization` | The header in which the api key needs to be included for authentication purposes. |

## PdfAct

Prefix: `PARXY_PDFACT_`

| Variable | Default | Description |
|----------|---------|-------------|
| `PARXY_PDFACT_BASE_URL` | `http://localhost:4567/` | The base URL of the PdfAct API. |
| `PARXY_PDFACT_API_KEY` | *(secret)* | The authentication key. |

## LlamaParse

Prefix: `PARXY_LLAMAPARSE_`

| Variable | Default | Description |
|----------|---------|-------------|
| `PARXY_LLAMAPARSE_BASE_URL` | `https://api.cloud.eu.llamaindex.ai` | The base URL of the LlamaParse API. |
| `PARXY_LLAMAPARSE_API_KEY` | *(secret)* | The authentication key. |
| `PARXY_LLAMAPARSE_ORGANIZATION_ID` | - | The organization ID for the LlamaParse API. |
| `PARXY_LLAMAPARSE_PROJECT_ID` | - | The project ID for the LlamaParse API. |
| `PARXY_LLAMAPARSE_TIER` | - | Parsing tier to use. One of: `fast`, `cost_effective`, `agentic`, `agentic_plus`. |
| `PARXY_LLAMAPARSE_VERSION` | `latest` | API version string. |
| `PARXY_LLAMAPARSE_PARSE_MODE` | - | Legacy parsing mode. |
| `PARXY_LLAMAPARSE_PREMIUM_MODE` | `false` | If True, selects the 'agentic_plus' tier (legacy shorthand). |
| `PARXY_LLAMAPARSE_FAST_MODE` | `false` | If True, selects the 'fast' tier (legacy shorthand). |
| `PARXY_LLAMAPARSE_DISABLE_OCR` | `false` | Disable OCR on images embedded in the document. |
| `PARXY_LLAMAPARSE_SKIP_DIAGONAL_TEXT` | `false` | Skip text rotated at an angle (e.g. |
| `PARXY_LLAMAPARSE_LANGUAGE` | `en` | Primary language for OCR (e.g. |
| `PARXY_LLAMAPARSE_DO_NOT_UNROLL_COLUMNS` | `false` | Keep multi-column layout intact instead of linearising columns into sequential text. |
| `PARXY_LLAMAPARSE_DISABLE_IMAGE_EXTRACTION` | `false` | If True, skip image extraction. |
| `PARXY_LLAMAPARSE_CONTINUOUS_MODE` | `false` | Automatically merge tables that span multiple pages. |
| `PARXY_LLAMAPARSE_TARGET_PAGES` | - | Specific pages to extract. |
| `PARXY_LLAMAPARSE_MAX_PAGES` | - | Maximum number of pages to extract. |
| `PARXY_LLAMAPARSE_DO_NOT_CACHE` | `true` | If True, bypass result caching and force re-parsing. |
| `PARXY_LLAMAPARSE_VERBOSE` | `false` | Print progress indicators during parsing. |

## LLMWhisperer

Prefix: `PARXY_LLMWHISPERER_`

| Variable | Default | Description |
|----------|---------|-------------|
| `PARXY_LLMWHISPERER_BASE_URL` | `https://llmwhisperer-api.eu-west.unstract.com/api/v2` | The base URL of the LlmWhisperer API v2. |
| `PARXY_LLMWHISPERER_API_KEY` | *(secret)* | The authentication key. |
| `PARXY_LLMWHISPERER_LOGGING_LEVEL` | `INFO` | The logging level for the client. |
| `PARXY_LLMWHISPERER_MODE` | `form` | Default parsing mode. |

## Landing AI

Prefix: `PARXY_LANDINGAI_`

| Variable | Default | Description |
|----------|---------|-------------|
| `PARXY_LANDINGAI_API_KEY` | *(secret)* | The authentication key. |
| `PARXY_LANDINGAI_ENVIRONMENT` | `eu` | The environment to use. One of: `production`, `eu`. |
| `PARXY_LANDINGAI_BASE_URL` | - | The base URL of the Landing AI ADE API. |

## Unstructured library

Prefix: `PARXY_UNSTRUCTURED_LOCAL_`

| Variable | Default | Description |
|----------|---------|-------------|

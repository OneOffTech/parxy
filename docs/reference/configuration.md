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
| `PARXY_LLAMAPARSE_BASE_URL` | `https://api.cloud.eu.llamaindex.ai` | The base URL of the Llama Parsing API. |
| `PARXY_LLAMAPARSE_API_KEY` | *(secret)* | The authentication key |
| `PARXY_LLAMAPARSE_ORGANIZATION_ID` | - | The organization ID for the LlamaParse API. |
| `PARXY_LLAMAPARSE_PROJECT_ID` | - | The project ID for the LlamaParse API. |
| `PARXY_LLAMAPARSE_NUM_WORKERS` | `4` | The number of workers to use sending API requests for parsing. |
| `PARXY_LLAMAPARSE_SHOW_PROGRESS` | `false` | Show progress when parsing multiple files. |
| `PARXY_LLAMAPARSE_VERBOSE` | `false` | Whether to print the progress of the parsing. |
| `PARXY_LLAMAPARSE_PARSE_MODE` | `parse_page_with_llm` | Parsing mode to use. |
| `PARXY_LLAMAPARSE_PRESET` | - | Parser preset. |
| `PARXY_LLAMAPARSE_MODEL` | - | Document model name for parse_with_agent mode. |
| `PARXY_LLAMAPARSE_PREMIUM_MODE` | `false` | Use best parser mode if set to True. |
| `PARXY_LLAMAPARSE_FAST_MODE` | `false` | Use faster mode that skips OCR of images and table/heading reconstruction. |
| `PARXY_LLAMAPARSE_DISABLE_OCR` | `false` | Disable the OCR on the document. |
| `PARXY_LLAMAPARSE_DISABLE_IMAGE_EXTRACTION` | `false` | If set to true, the parser will not extract images from the document. |
| `PARXY_LLAMAPARSE_HIGH_RES_OCR` | `false` | Use high resolution OCR to extract text from images. |
| `PARXY_LLAMAPARSE_EXTRACT_LAYOUT` | `false` | Extract layout information from the document. |
| `PARXY_LLAMAPARSE_SKIP_DIAGONAL_TEXT` | `false` | Skip diagonal text (when text rotation in degrees modulo 90 is not 0). |
| `PARXY_LLAMAPARSE_LANGUAGE` | `en` | Language of the text to parse. |
| `PARXY_LLAMAPARSE_DO_NOT_UNROLL_COLUMNS` | `false` | Keep columns in text according to document layout. |
| `PARXY_LLAMAPARSE_TARGET_PAGES` | - | Target pages to extract. |
| `PARXY_LLAMAPARSE_MAX_PAGES` | - | Maximum number of pages to extract. |
| `PARXY_LLAMAPARSE_CONTINUOUS_MODE` | `false` | Parse documents continuously for better results on tables spanning multiple pages. |
| `PARXY_LLAMAPARSE_AUTO_MODE` | `false` | Automatically select best mode based on page content. |
| `PARXY_LLAMAPARSE_DO_NOT_CACHE` | `true` | If set to true, the document will not be cached. |

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

---
title: Installation and setup
description: Quick instructions to install Parxy via pip, uv, or uvx and configuration via environment variables.
weight: 3
---

# Installation and Setup

## Requirements

- Python **3.12** or **3.13**

## Installation

Parxy can be installed via pip or uv, or run without installation using uvx.

### Via pip

```bash
pip install parxy        # Basic installation (PyMuPDF and PdfAct drivers)
pip install parxy[all]   # All drivers included
```

### Via uv

```bash
uv add parxy             # Basic installation
uv add parxy --extra all # All drivers included
```

### Without installation (uvx)

[`uvx`](https://docs.astral.sh/uv/guides/tools/) runs Parxy in an isolated environment without a permanent install:

```bash
# Basic drivers only
uvx parxy --help
```

```bash
# All drivers included
uvx --from 'parxy[all]' parxy --help
```

### Installing specific drivers

If you only need a particular driver, install its extra instead of `all`:

```bash
pip install parxy[llama]          # LlamaParse
pip install parxy[llmwhisperer]   # LLMWhisperer
pip install parxy[landingai]      # Landing AI
pip install parxy[unstructured_local]  # Unstructured library
```

See [Supported Services](./supported_services.md) for the full list of drivers and their extras.

## Environment variables and API keys

Some drivers require an API key. Parxy reads these from environment variables, which can be set in a `.env` file in your project root.

To generate a template `.env` file:

```bash
parxy env
```

Then fill in the keys for the services you use:

```bash
# LlamaParse
PARXY_LLAMAPARSE_API_KEY=

# Unstract LLMWhisperer
PARXY_LLMWHISPERER_API_KEY=
```

### Core environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PARXY_DEFAULT_DRIVER` | `pymupdf` | Driver used when none is specified |
| `PARXY_LOGGING_LEVEL` | `INFO` | Logging verbosity |
| `PARXY_LOGGING_FILE` | *(none)* | Path to write log output |

### Self-hosted services

Some drivers (such as PdfAct) can be run locally via Docker. To generate a Docker Compose configuration:

```bash
parxy docker
```

This produces a `compose.yaml` you can start with `docker compose up`.

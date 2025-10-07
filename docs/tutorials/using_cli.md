# Using the Parxy Command Line Interface (CLI)

Parxy provides a powerful and flexible **command-line interface (CLI)** that allows you to parse documents, convert them to Markdown, and manage configuration files directly from your terminal — without writing any Python code.

Once [installed](./getting_started.md), you can run the CLI via the `parxy` command.

## Overview

The Parxy CLI lets you:

| Command          | Description                                                                                                 |
|------------------|-------------------------------------------------------------------------------------------------------------|
| `parxy parse`    | Extract text content from documents with customizable detail levels (page, block, line, span, or character) |
| `parxy markdown` | Convert parsed documents into Markdown format (optionally combine multiple files)                           |
| `parxy drivers`  | List available document processing drivers                                                                  |
| `parxy env`      | Generate a default `.env` configuration file                                                                |
| `parxy docker`   | Create a Docker Compose configuration for running Parxy-related services                                    |


## Parsing Documents

The `parse` command extracts text from one or more documents.

```bash
parxy parse document.pdf
```

By default, Parxy uses the **PyMuPDF** driver and extracts text at the **block** level of granularity.

You can adjust the extraction level with the `--level` (`-l`) option:

```bash
parxy parse --level line document.pdf
```

Supported levels are (depending on the driver):

* `page`
* `block` (default)
* `line`
* `span`
* `character`

You can also specify a different driver:

```bash
parxy parse --driver llamaparse document.pdf
```

To save the output instead of printing it, specify an output directory:

```bash
parxy parse -o output/ document.pdf
```

Each file will be saved as a `.txt` file with the same base name as the input.

To quickly preview only part of the extracted text, use the `--preview` option (e.g. first 500 characters):

```bash
parxy parse --preview 500 document.pdf
```


## Converting to Markdown

The `markdown` command converts parsed documents into Markdown format, preserving structure such as headings and lists.

```bash
parxy markdown document.pdf
```

Output is printed to the console by default. To save Markdown files to disk:

```bash
parxy markdown -o output/ document1.pdf document2.pdf
```

Each document will be saved as a `.md` file.

To combine multiple documents into a single Markdown file:

```bash
parxy markdown --combine -o output/ doc1.pdf doc2.pdf doc3.pdf
```

This will generate a file named `combined_output.md` in the output directory.


## Managing Drivers

To view the list of supported document parsing drivers:

```bash
parxy drivers
```

This will display all available backends (e.g., `pymupdf`, `pdfact`, `llamaparse`, etc.).


## Environment Configuration

To create a default `.env` configuration file for Parxy:

```bash
parxy env
```

If a `.env` file already exists, you'll be prompted before overwriting it.
You can then edit this file to adjust driver settings, API keys, or other environment variables.


## Running with Docker

Parxy can generate a ready-to-use Docker Compose configuration for self-hosted services (e.g., parsers available via an http-based api):

```bash
parxy docker
```

This creates a `compose.yaml` file in your working directory.
To start the services, run:

```bash
docker compose pull
docker compose up -d
```


## Full Command Reference

Run the following to see all available commands and options:

```bash
parxy --help
```

Each command also supports `--help` for detailed usage, for example:

```bash
parxy parse --help
```


## Summary

With the CLI, you can use Parxy as a **standalone document parsing tool** — ideal for quick experiments, batch conversions, or integrations in shell-based pipelines.

| Command          | Purpose                           |
|------------------|-----------------------------------|
| `parxy parse`    | Extract text from documents       |
| `parxy markdown` | Generate Markdown output          |
| `parxy drivers`  | List supported drivers            |
| `parxy env`      | Create default configuration file |
| `parxy docker`   | Generate Docker Compose setup     |

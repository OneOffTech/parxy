# Using the Parxy Command Line Interface (CLI)

Parxy provides a powerful and flexible **command-line interface (CLI)** that allows you to parse documents, convert them to Markdown, and manage configuration files directly from your terminal — without writing any Python code.

Once [installed](./getting_started.md), you can run the CLI via the `parxy` command.

## Overview

The Parxy CLI lets you:

| Command          | Description                                                                                                 |
|------------------|-------------------------------------------------------------------------------------------------------------|
| `parxy parse`    | Extract text content from documents with customizable detail levels and output formats. Process files or folders with multiple drivers. |
| `parxy preview`  | Interactive document viewer with metadata, table of contents, and scrollable content preview                |
| `parxy markdown` | Convert parsed documents into Markdown format (optionally combine multiple files)                           |
| `parxy drivers`  | List available document processing drivers                                                                  |
| `parxy env`      | Generate a default `.env` configuration file                                                                |
| `parxy docker`   | Create a Docker Compose configuration for running Parxy-related services                                    |


## Parsing Documents

The `parse` command is a powerful tool for extracting text from documents with extensive customization options. It supports processing individual files or entire folders, multiple output formats, and can use multiple drivers for comparison.

### Basic Usage

Parse a single document using the default settings (PyMuPDF driver, markdown output):

```bash
parxy parse document.pdf
```

This creates a `document.md` file in the same directory as the source file.

### Processing Multiple Files and Folders

Parse multiple files at once:

```bash
parxy parse doc1.pdf doc2.pdf doc3.pdf
```

Process all PDFs in a folder (recursively):

```bash
parxy parse /path/to/folder
```

Mix files and folders:

```bash
parxy parse document.pdf /path/to/folder
```

### Output Formats

Control the output format with the `--mode` (`-m`) option:

```bash
# Markdown format (default)
parxy parse document.pdf -m markdown

# Plain text
parxy parse document.pdf -m plain

# JSON (full document structure)
parxy parse document.pdf -m json
```

The file extension is automatically set based on the output mode (`.md`, `.txt`, or `.json`).

### Output Directory

Specify where to save the output files with `--output` (`-o`):

```bash
parxy parse document.pdf -o output/
```

If not specified, files are saved in the same directory as the source files.

### Extraction Levels

Adjust the extraction level with the `--level` (`-l`) option:

```bash
parxy parse --level line document.pdf
```

Supported levels are (depending on the driver):

* `page`
* `block` (default)
* `line`
* `span`
* `character`

### Using Different Drivers

Specify a driver with the `--driver` (`-d`) option:

```bash
parxy parse --driver llamaparse document.pdf
```

### Using Multiple Drivers for Comparison

Parse the same document(s) with multiple drivers by specifying `--driver` multiple times:

```bash
parxy parse document.pdf -d pymupdf -d llamaparse
```

When using multiple drivers, Parxy automatically appends the driver name to the output filenames:
- `document_pymupdf.md`
- `document_llamaparse.md`

This is particularly useful for comparing extraction quality across different parsers.

### Showing Output in Console

By default, output is only saved to files. To also display content in the console, use the `--show` (`-s`) flag:

```bash
parxy parse document.pdf --show
```

### Progress Tracking

When processing multiple files, Parxy displays a progress bar showing:
- Files being processed
- Driver being used
- Output file location
- Number of pages extracted

### Complete Example

Process all PDFs in a folder with two drivers, output as JSON, and save to a specific directory:

```bash
parxy parse /path/to/pdfs -d pymupdf -d llamaparse -m json -o output/
```

## Previewing Documents

The `preview` command provides an interactive document viewer that displays:
- Document metadata (title, author, creation date, etc.)
- Table of contents extracted from headings
- Document content rendered as markdown

This is useful for quickly inspecting a document's structure and content without creating output files.

### Basic Usage

```bash
parxy preview document.pdf
```

The preview is displayed in a scrollable three-panel layout.

### Options

Specify a driver:

```bash
parxy preview document.pdf --driver llamaparse
```

Adjust extraction level:

```bash
parxy preview document.pdf --level line
```

### Navigation

The preview uses your system's default pager (similar to `less` on Unix systems), allowing you to:
- Scroll up and down
- Search for text
- Exit the preview

This is ideal for quick document inspection before running a full parsing operation.


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

| Command          | Purpose                                                      |
|------------------|--------------------------------------------------------------|
| `parxy parse`    | Extract text from documents with multiple formats & drivers  |
| `parxy preview`  | Interactive document viewer with metadata and TOC            |
| `parxy markdown` | Generate Markdown output                                     |
| `parxy drivers`  | List supported drivers                                       |
| `parxy env`      | Create default configuration file                            |
| `parxy docker`   | Generate Docker Compose setup                                |

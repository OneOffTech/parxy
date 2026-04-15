---
title: CLI reference
description: Command line reference with all parxy commands, including arguments, options, types, and defaults. Prefer to run parxy --help and parxy <command> --help if you have access to the terminal.
---

<!-- This file is auto-generated from the source code. Do not edit it manually. -->
<!-- Regenerate with: python scripts/generate_docs.py -->

# CLI reference

## `parxy agents`

Set up AI agent configuration files for Parxy projects.

Creates or updates an AGENTS.md file with Parxy usage documentation.
If AGENTS.md exists, the Parxy section (marked with <parxy> tags) is
added or updated while preserving other content.

Optionally creates Claude Code skill files for common operations.

```
parxy agents [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | `path` | - | Output directory for agent files. Defaults to current directory. |
| `--overwrite` | `-f` | `flag` | `false` | Overwrite existing Parxy section without prompting. |

## `parxy attach`

Extract an attached file from a PDF

```
parxy attach [OPTIONS] INPUT_FILE NAME
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUT_FILE` | Yes | PDF file containing the attachment |
| `NAME` | Yes | Name of attached file to extract |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | `text` | - | Output file path. If not specified, saves to current directory with original name. |
| `--stdout` | - | `flag` | `false` | Output content to stdout (text files only) |

## `parxy attach:add`

Add files as attachments to a PDF

```
parxy attach:add [OPTIONS] INPUT_FILE FILES...
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUT_FILE` | Yes | PDF file to add attachments to |
| `FILES` | Yes | One or more files to attach |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | `text` | - | Output file path. If not specified, creates {input}_with_attachments.pdf |
| `--description` | `-d` | `text` | - | Description for attached file(s). Matched by position to files. |
| `--name` | `-n` | `text` | - | Custom name(s) for attached file(s). Matched by position to files. |
| `--overwrite` | - | `flag` | `false` | Overwrite existing attachments with same name |

## `parxy attach:list`

List attached files in a PDF

```
parxy attach:list [OPTIONS] INPUT_FILE
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUT_FILE` | Yes | PDF file to inspect |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--verbose` | `-v` | `flag` | `false` | Show detailed information |

## `parxy attach:remove`

Remove attached files from a PDF

```
parxy attach:remove [OPTIONS] INPUT_FILE NAMES...
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUT_FILE` | Yes | PDF file to process |
| `NAMES` | No | Names of attachments to remove |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | `text` | - | Output file path. If not specified, creates {input}_no_attachments.pdf |
| `--all` | - | `flag` | `false` | Remove all attached files |

## `parxy docker`

Create a Docker Compose file to run self-hostable parsers (experimental).

```
parxy docker
```

## `parxy drivers`

List supported drivers.

```
parxy drivers
```

## `parxy env`

Create an environment file with Parxy configuration.

```
parxy env
```

## `parxy markdown`

Parse documents to Markdown.

Accepts PDF files (parsed on-the-fly) or pre-parsed JSON result files
(loaded directly from the Document model without re-parsing).

```
parxy markdown [OPTIONS] INPUTS...
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUTS` | Yes | One or more files or folders to parse. Use --recursive to search subdirectories. |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--driver` | `-d` | `text` | - | Driver(s) to use for parsing. Can be specified multiple times. (default: pymupdf or PARXY_DEFAULT_DRIVER) |
| `--level` | `-l` | `page` | `block` | `line` | `span` | `character` | `block` | Extraction level |
| `--output` | `-o` | `text` | - | Directory to save markdown files. If not specified, files are saved next to the source files. |
| `--inline` | `-i` | `flag` | `false` | Output markdown to stdout with file name as YAML frontmatter. Only valid with a single file. |
| `--recursive` | `-r` | `flag` | `false` | Recursively search subdirectories when processing folders |
| `--max-depth` | - | `integer range` | - | Maximum depth to recurse into subdirectories (only applies with --recursive). 0 = current directory only, 1 = one level down, etc. |
| `--stop-on-failure` | - | `flag` | `false` | Stop processing files immediately if an error occurs with any file |
| `--workers` | `-w` | `integer range` | - | Number of parallel workers to use. Defaults to cpu count. |
| `--page-separators` | - | `flag` | `false` | Insert <!-- page: N --> HTML comments before each page's content. |

## `parxy parse`

Parse documents using one or more drivers.

This command processes PDF documents and extracts their content in various formats.
You can specify individual files or entire folders to process.

```
parxy parse [OPTIONS] INPUTS...
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUTS` | Yes | One or more files or folders to parse. Use --recursive to search subdirectories. |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--driver` | `-d` | `text` | - | Driver(s) to use for parsing. Can be specified multiple times. (default: pymupdf or PARXY_DEFAULT_DRIVER) |
| `--level` | `-l` | `page` | `block` | `line` | `span` | `character` | `block` | Extraction level |
| `--mode` | `-m` | `json` | `plain` | `markdown` | `json` | Output mode: json (JSON serialization), plain (plain text), or markdown (markdown format) |
| `--output` | `-o` | `text` | - | Directory to save output files. If not specified, files will be saved in the same directory as the source files. |
| `--show` | `-s` | `flag` | `false` | Show document content in console in addition to saving to files |
| `--recursive` | `-r` | `flag` | `false` | Recursively search subdirectories when processing folders |
| `--max-depth` | - | `integer range` | - | Maximum depth to recurse into subdirectories (only applies with --recursive). 0 = current directory only, 1 = one level down, etc. |
| `--stop-on-failure` | - | `flag` | `false` | Stop processing files immediately if an error occurs with any file |
| `--workers` | `-w` | `integer range` | - | Number of parallel workers to use. Defaults to cpu count. |

## `parxy pdf:merge`

Merge multiple PDF files into a single PDF

```
parxy pdf:merge [OPTIONS] INPUTS...
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUTS` | Yes | One or more PDF files or folders to merge. Files support page ranges in square brackets (e.g., file.pdf[1:3]). Folders are processed non-recursively. |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | `text` | - | Output file path for the merged PDF. If not specified, you will be prompted. |

## `parxy pdf:split`

Split a PDF file into individual pages

```
parxy pdf:split [OPTIONS] INPUT_FILE
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUT_FILE` | Yes | PDF file to split |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | `text` | - | Output path. Without --combine: output directory for split files (default: folder next to input). With --combine: output file path (default: {stem}_pages_{from}-{to}.pdf next to input). |
| `--prefix` | `-p` | `text` | - | Prefix for output filenames. If not specified, uses the input filename. |
| `--pages` | - | `text` | - | Page range to extract (1-based). Examples: "1" (single page), "1:3" (pages 1-3), ":3" (up to page 3), "3:" (from page 3). If not specified, all pages are extracted. |
| `--combine` | - | `flag` | `false` | Combine extracted pages into a single PDF instead of one file per page. |

## `parxy tui`

Launch the Parxy TUI for interactive parser comparison

```
parxy tui WORKSPACE
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `WORKSPACE` | No | Path to the workspace folder (optional — can be selected inside the TUI) |

## `parxy version`

Print Parxy version information.

```
parxy version
```

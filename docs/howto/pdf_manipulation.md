# How to Manipulate PDFs with Parxy

Parxy provides powerful **PDF manipulation commands** that allow you to merge multiple PDF files into one or split a single PDF into multiple files — all from the command line.

These commands are useful for:
- Combining multiple PDF documents into a single file
- Extracting specific page ranges from PDFs
- Splitting large PDFs into smaller, manageable files
- Reorganizing PDF pages

## Merging PDFs

The `pdf:merge` command combines multiple PDF files into a single output file, with support for selecting specific page ranges.

### Basic Merging

Merge two or more PDF files:

```bash
parxy pdf:merge file1.pdf file2.pdf -o merged.pdf
```

If you don't specify an output file, you'll be prompted to enter one:

```bash
parxy pdf:merge file1.pdf file2.pdf
# Prompts: Enter output filename or path: merged.pdf
```

### Merging Entire Folders

You can merge all PDFs in a folder (non-recursively):

```bash
parxy pdf:merge /path/to/folder -o combined.pdf
```

Files from folders are included in alphabetical order.

### Combining Files and Folders

Mix individual files and folders:

```bash
parxy pdf:merge cover.pdf /path/to/chapters appendix.pdf -o book.pdf
```

### Selecting Specific Pages

Use square brackets to specify page ranges (1-based indexing):

**Single page:**
```bash
parxy pdf:merge document.pdf[1] -o first_page.pdf
```

**Page range:**
```bash
parxy pdf:merge document.pdf[1:3] -o first_three_pages.pdf
```

**From start to page N:**
```bash
parxy pdf:merge document.pdf[:5] -o first_five_pages.pdf
```

**From page N to end:**
```bash
parxy pdf:merge document.pdf[10:] -o from_page_10.pdf
```

### Advanced Merging Examples

**Combine specific pages from multiple documents:**
```bash
parxy pdf:merge doc1.pdf[1] doc2.pdf[2:4] doc3.pdf[:2] -o selected_pages.pdf
```

**Mix full files with page ranges:**
```bash
parxy pdf:merge cover.pdf report.pdf[1:10] summary.pdf appendix.pdf[5:] -o final_report.pdf
```

**Merge chapter files:**
```bash
parxy pdf:merge intro.pdf chapter1.pdf chapter2.pdf chapter3.pdf conclusion.pdf -o complete_book.pdf
```

### Output Path Handling

- If you provide a full path, the file is created there
- If you provide just a filename, it's created in the same directory as the first input file
- The `.pdf` extension is added automatically if not provided

```bash
# Creates merged.pdf in the same directory as file1.pdf
parxy pdf:merge file1.pdf file2.pdf -o merged

# Creates in specified directory
parxy pdf:merge file1.pdf file2.pdf -o /output/dir/merged.pdf
```

## Splitting PDFs

The `pdf:split` command divides a single PDF into individual pages, with each page becoming a separate PDF file. You can optionally limit which pages are extracted and combine them into a single output PDF.

### Basic Splitting

Split a PDF into individual pages:

```bash
parxy pdf:split document.pdf
```

This creates a folder named `document_split/` containing:
- `document_page_1.pdf`
- `document_page_2.pdf`
- `document_page_3.pdf`
- etc.

### Custom Output Directory

Specify where to save the split files:

```bash
parxy pdf:split document.pdf --output /path/to/output
```

### Custom Filename Prefix

Change the prefix of output filenames:

```bash
parxy pdf:split book.pdf --prefix chapter
```

Creates files named:
- `chapter_page_1.pdf`
- `chapter_page_2.pdf`
- etc.

### Extracting a Page Range

Use `--pages` to limit which pages are extracted (1-based indexing):

**Single page:**
```bash
parxy pdf:split document.pdf --pages 3
```

**Page range:**
```bash
parxy pdf:split document.pdf --pages 2:5
```

**From start to page N:**
```bash
parxy pdf:split document.pdf --pages :5
```

**From page N to end:**
```bash
parxy pdf:split document.pdf --pages 3:
```

### Combining Pages into a Single PDF

Use `--combine` to extract a page range into a single output PDF instead of one file per page:

```bash
# Extract pages 2–5 as a single PDF (auto-named)
parxy pdf:split document.pdf --pages 2:5 --combine
# Output: document_pages_2-5.pdf (next to the input file)

# Specify a custom output path
parxy pdf:split document.pdf --pages 2:5 --combine -o extracted.pdf

# Extract a single page as a PDF
parxy pdf:split document.pdf --pages 3 --combine -o page3.pdf

# Combine all pages (equivalent to a copy)
parxy pdf:split document.pdf --combine -o copy.pdf
```

> **Tip:** `--combine` pairs well with `--pages` to replace the `pdf:merge file.pdf[2:5]` pattern when working with a single source file.

### Complete Examples

**Split with custom output directory:**
```bash
parxy pdf:split annual_report.pdf -o ./pages
```

**Split with custom prefix:**
```bash
parxy pdf:split presentation.pdf --prefix slide
```

Creates:
- `slide_page_1.pdf`
- `slide_page_2.pdf`
- etc.

**Split with both custom output and prefix:**
```bash
parxy pdf:split document.pdf -o ./individual_pages -p page
```

**Extract pages 10–20 as individual files:**
```bash
parxy pdf:split document.pdf --pages 10:20 -o ./extracted_pages
```

## Combining Merge and Split

You can chain operations together using the CLI:

**Example: Extract specific pages and split them:**
```bash
# Extract pages 10-20 as individual files
parxy pdf:split document.pdf --pages 10:20 -o ./individual_pages
```

**Example: Extract a range into a single PDF, then split:**
```bash
# First, extract pages 10-20 into one PDF
parxy pdf:split document.pdf --pages 10:20 --combine -o extracted.pdf

# Then split into individual pages
parxy pdf:split extracted.pdf -o ./individual_pages
```

**Example: Merge and organize:**
```bash
# Merge selected pages from multiple documents
parxy pdf:merge doc1.pdf[1:5] doc2.pdf[3:8] -o combined.pdf

# Split the combined result into individual pages
parxy pdf:split combined.pdf -o ./pages -p combined_page
```

## Tips and Best Practices

### Page Numbering
- All page ranges use **1-based indexing** (first page is page 1, not 0)
- Ranges are **inclusive** (e.g., `[1:3]` includes pages 1, 2, and 3)

### File Organization
- Use folders to keep merged/split files organized
- Use descriptive prefixes to make file purposes clear
- Split creates a dedicated folder by default to avoid clutter

### Performance
- Both commands are optimized for speed
- Large PDFs are processed efficiently
- Progress information is displayed during processing

### Error Handling
- Invalid page ranges are reported with warnings
- Missing files are detected before processing starts
- The commands validate input before making changes

## Command Reference

### pdf:merge

```bash
parxy pdf:merge [FILES...] --output OUTPUT
```

**Arguments:**
- `FILES`: One or more PDF files or folders. Supports page ranges: `file.pdf[1:3]`

**Options:**
- `--output, -o`: Output file path (prompted if not provided)

**Examples:**
```bash
parxy pdf:merge file1.pdf file2.pdf -o merged.pdf
parxy pdf:merge folder1/ file.pdf folder2/ -o combined.pdf
parxy pdf:merge doc.pdf[1:10] doc.pdf[20:30] -o selections.pdf
```

### pdf:split

```bash
parxy pdf:split INPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE`: PDF file to split

**Options:**
- `--output, -o`: Without `--combine`: output directory (default: `{filename}_split/`). With `--combine`: output file path (default: `{filename}_pages_{from}-{to}.pdf` next to the input).
- `--prefix, -p`: Output filename prefix for individual split files (default: input filename)
- `--pages`: Page range to extract, 1-based. Formats: `3` (single page), `2:5` (range), `:5` (up to page 5), `3:` (from page 3 to end)
- `--combine`: Combine extracted pages into a single PDF instead of one file per page

**Examples:**
```bash
parxy pdf:split document.pdf
parxy pdf:split document.pdf -o ./pages
parxy pdf:split document.pdf -o ./pages -p page
parxy pdf:split document.pdf --pages 2:5
parxy pdf:split document.pdf --pages 2:5 --combine -o extracted.pdf
```

## Getting Help

For detailed command usage, use the `--help` flag:

```bash
parxy pdf:merge --help
parxy pdf:split --help
```

# How to Work with PDF Attachments

Parxy provides comprehensive **PDF attachment commands** that allow you to add, list, extract, and remove file attachments in PDF documents — all from the command line.

PDF attachments (also known as embedded files or file attachments) are files that you can store inside a PDF document. They're useful for:
- Bundling related data files with reports (CSV, Excel, JSON)
- Including source files with documentation
- Attaching code or configuration files to technical PDFs
- Distributing multiple files as a single PDF package
- Archiving related documents together

## Understanding PDF Attachments

PDF attachments are files that are embedded directly into the PDF structure. They:
- Don't appear on the PDF pages (they're not visible content)
- Can be accessed through PDF viewers that support attachments
- Preserve the original file format and content
- Include metadata like filename and description
- Can be any file type (text, binary, images, archives, etc.)

## Listing Attachments

The `attach:list` command shows all files attached to a PDF document.

### Basic Listing

View all attachments in a PDF:

```bash
parxy attach:list document.pdf
```

Example output:
```
Found 3 attached files in document.pdf:

⎿ data.csv
⎿ notes.txt
⎿ config.json
```

### Verbose Listing

Show detailed information including file sizes and descriptions:

```bash
parxy attach:list document.pdf --verbose
# or
parxy attach:list document.pdf -v
```

Example output:
```
Found 3 attached files in document.pdf:

⎿ data.csv (45.2 KB) - Q4 Sales Data
⎿ notes.txt (2.1 KB) - Meeting notes from review
⎿ config.json (1.5 KB) - Configuration parameters
```

## Adding Attachments

The `attach:add` command embeds files into a PDF document.

### Add a Single File

Attach one file to a PDF:

```bash
parxy attach:add report.pdf data.csv -o report_with_data.pdf
```

If you don't specify an output filename, Parxy creates `{input}_with_attachments.pdf`:

```bash
parxy attach:add report.pdf data.csv
# Creates: report_with_attachments.pdf
```

### Add Multiple Files

Attach several files at once:

```bash
parxy attach:add report.pdf data.csv notes.txt config.json -o enhanced_report.pdf
```

### Add with Custom Names

Give attachments custom names inside the PDF:

```bash
parxy attach:add report.pdf quarterly_data.csv --name "Q1_2024.csv" -o report.pdf
```

The file will appear in the PDF as "Q1_2024.csv" instead of "quarterly_data.csv".

### Add with Descriptions

Include descriptions for your attachments:

```bash
parxy attach:add report.pdf data.csv --description "Sales data for Q4 2024" -o report.pdf
```

### Add Multiple Files with Descriptions

Match descriptions to files by position:

```bash
parxy attach:add report.pdf \
  sales.csv revenue.csv expenses.csv \
  --description "Q4 Sales Data" \
  --description "Q4 Revenue Breakdown" \
  --description "Q4 Expense Report" \
  -o financial_report.pdf
```

You can provide fewer descriptions than files. Files without descriptions won't have one:

```bash
parxy attach:add report.pdf file1.csv file2.csv file3.csv \
  --description "First file description" \
  -o report.pdf
# Only file1.csv has a description
```

### Overwrite Existing Attachments

By default, adding a file with the same name as an existing attachment fails:

```bash
parxy attach:add report.pdf data.csv -o updated.pdf
# Error: Attachment 'data.csv' already exists in report.pdf
# Use --overwrite to replace it
```

Use `--overwrite` to replace existing attachments:

```bash
parxy attach:add report.pdf updated_data.csv --name data.csv --overwrite -o report.pdf
```

## Extracting Attachments

The `attach` command (or its alias `attach:read`) extracts attached files from a PDF.

### Extract to Current Directory

Extract an attachment to the current directory:

```bash
parxy attach document.pdf data.csv
```

This creates `data.csv` in your current directory.

### Extract to Specific Path

Specify where to save the extracted file:

```bash
parxy attach document.pdf data.csv -o /path/to/output.csv
```

### Extract Multiple Files

Extract files one by one:

```bash
parxy attach report.pdf sales.csv -o ./data/sales.csv
parxy attach report.pdf notes.txt -o ./data/notes.txt
```

### View Text Files in Terminal

For text files, you can output directly to stdout:

```bash
parxy attach document.pdf notes.txt --stdout
```

This prints the file content to your terminal. Great for quickly viewing text attachments!

**Note:** Binary files cannot be output to stdout:

```bash
parxy attach document.pdf image.png --stdout
# Error: Cannot output binary file to stdout.
# Use -o to save to a file instead.
```

## Removing Attachments

The `attach:remove` command removes attached files from a PDF.

### Remove a Single Attachment

Remove one attachment by name:

```bash
parxy attach:remove document.pdf old_data.csv -o cleaned.pdf
```

If you don't specify output, Parxy creates `{input}_no_attachments.pdf`:

```bash
parxy attach:remove document.pdf old_data.csv
# Creates: document_no_attachments.pdf
```

### Remove Multiple Attachments

Remove several attachments at once:

```bash
parxy attach:remove document.pdf file1.csv file2.txt file3.json -o cleaned.pdf
```

### Remove All Attachments

Remove all attachments from a PDF (with confirmation):

```bash
parxy attach:remove document.pdf --all -o clean.pdf
```

You'll be prompted to confirm:
```
This will remove the following attached files from document.pdf:
⎿ data.csv and 3 more

Continue? [y/N]:
```

Type `y` to proceed or `n` to cancel.

### Handle Non-Existent Attachments

If you try to remove an attachment that doesn't exist, you'll see available options:

```bash
parxy attach:remove document.pdf nonexistent.csv -o output.pdf
# Error: Attachment 'nonexistent.csv' not found in document.pdf
#
# Available attachments:
# ⎿ data.csv
# ⎿ notes.txt
# ⎿ config.json
```

## Advanced Usage Examples

### Workflow: Update Attachment

Replace an outdated file with a new version:

```bash
# Remove old version
parxy attach:remove report.pdf old_data.csv -o temp.pdf

# Add new version
parxy attach:add temp.pdf new_data.csv --name data.csv -o report.pdf

# Clean up
rm temp.pdf
```

Or use `--overwrite` for a single step:

```bash
parxy attach:add report.pdf new_data.csv --name data.csv --overwrite -o report.pdf
```

### Workflow: Bundle Research Data

Attach all data files to a research paper:

```bash
parxy attach:add paper.pdf \
  experiment_data.csv \
  analysis_code.py \
  raw_results.json \
  --description "Experimental measurements from lab trials" \
  --description "Python analysis script" \
  --description "Raw output from analysis pipeline" \
  -o paper_with_data.pdf
```

### Workflow: Extract All Attachments

List and extract all attachments from a PDF:

```bash
# First, list all attachments
parxy attach:list document.pdf

# Then extract each one
parxy attach document.pdf data.csv -o ./extracted/data.csv
parxy attach document.pdf notes.txt -o ./extracted/notes.txt
parxy attach document.pdf config.json -o ./extracted/config.json
```

### Workflow: Create Self-Contained Report

Bundle everything needed to reproduce your analysis:

```bash
# Start with your report PDF
# Add the source data
parxy attach:add report.pdf raw_data.csv \
  --description "Source data for all analyses" \
  -o temp1.pdf

# Add processing scripts
parxy attach:add temp1.pdf process.py \
  --description "Data processing script" \
  -o temp2.pdf

# Add configuration
parxy attach:add temp2.pdf config.yaml \
  --description "Analysis configuration" \
  -o report_complete.pdf

# Clean up temporary files
rm temp1.pdf temp2.pdf
```

Or chain it all together:

```bash
parxy attach:add report.pdf \
  raw_data.csv process.py config.yaml \
  --description "Source data for all analyses" \
  --description "Data processing script" \
  --description "Analysis configuration" \
  -o report_complete.pdf
```

## Tips and Best Practices

### Naming Conventions

- Use descriptive filenames for attachments
- Include dates or versions in filenames when relevant
- Use consistent naming schemes for similar files
- Consider the filename as it will appear to PDF readers

### File Organization

- Group related files together in PDFs
- Use descriptions to explain what each attachment contains
- Remove outdated attachments before adding new versions
- List attachments periodically to verify PDF contents

### File Size Considerations

- Attachments increase PDF file size
- Use compression for large attachments when possible
- Consider splitting very large datasets across multiple PDFs
- Use `attach:list -v` to monitor attachment sizes

### Compatibility

- Most modern PDF viewers support attachments
- Some older or basic PDF viewers may not display them
- Attachments work across all platforms (Windows, Mac, Linux)
- The PDF specification has supported attachments since PDF 1.3

### Security

- Be cautious when opening attachments from untrusted PDFs
- Attachments preserve their original file type and can contain any data
- Scan extracted attachments with antivirus software if needed
- Consider signing PDFs that contain sensitive attachments

## Command Reference

### attach:list

```bash
parxy attach:list INPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE`: PDF file to inspect

**Options:**
- `--verbose, -v`: Show detailed information including file sizes and descriptions

**Examples:**
```bash
parxy attach:list document.pdf
parxy attach:list document.pdf -v
```

### attach:add

```bash
parxy attach:add INPUT_FILE FILES... [OPTIONS]
```

**Arguments:**
- `INPUT_FILE`: PDF file to add attachments to
- `FILES`: One or more files to attach

**Options:**
- `--output, -o`: Output file path (default: `{input}_with_attachments.pdf`)
- `--description, -d`: Description for attached file(s), matched by position
- `--name, -n`: Custom name(s) for attached file(s), matched by position
- `--overwrite`: Replace existing attachments with the same name

**Examples:**
```bash
parxy attach:add report.pdf data.csv -o enhanced.pdf
parxy attach:add report.pdf file1.csv file2.csv -o report.pdf
parxy attach:add report.pdf data.csv -d "Q4 Sales" -o report.pdf
parxy attach:add report.pdf new.csv --name data.csv --overwrite -o report.pdf
```

### attach (attach:read)

```bash
parxy attach INPUT_FILE NAME [OPTIONS]
```

**Arguments:**
- `INPUT_FILE`: PDF file containing the attachment
- `NAME`: Name of attached file to extract

**Options:**
- `--output, -o`: Output file path (default: current directory with original name)
- `--stdout`: Output content to stdout (text files only)

**Examples:**
```bash
parxy attach document.pdf data.csv
parxy attach document.pdf data.csv -o ./output/data.csv
parxy attach document.pdf notes.txt --stdout
```

### attach:remove

```bash
parxy attach:remove INPUT_FILE [NAMES...] [OPTIONS]
```

**Arguments:**
- `INPUT_FILE`: PDF file to remove attachments from
- `NAMES`: Names of attachments to remove (required unless `--all` is used)

**Options:**
- `--output, -o`: Output file path (default: `{input}_no_attachments.pdf`)
- `--all`: Remove all attached files (prompts for confirmation)

**Examples:**
```bash
parxy attach:remove document.pdf old.csv -o cleaned.pdf
parxy attach:remove document.pdf file1.csv file2.txt -o cleaned.pdf
parxy attach:remove document.pdf --all -o clean.pdf
```

## Getting Help

For detailed command usage, use the `--help` flag:

```bash
parxy attach:list --help
parxy attach:add --help
parxy attach --help
parxy attach:remove --help
```

## Related Documentation

- [PDF Manipulation](./pdf_manipulation.md) - Learn about merging and splitting PDFs
- [Getting Started Tutorial](../tutorials/getting_started.md) - General introduction to Parxy CLI
- [Using the CLI](../tutorials/using_cli.md) - Basic CLI usage patterns

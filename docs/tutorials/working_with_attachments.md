# Tutorial: Working with PDF Attachments

In this tutorial, you'll learn how to incorporate file attachments into PDF documents using Parxy's attachment commands. We'll walk through a real-world scenario where you need to bundle data files with a report.

## Prerequisites

- Parxy installed on your system
- Basic familiarity with the command line
- A PDF file to work with (or you can create a simple one)

## What You'll Learn

By the end of this tutorial, you'll be able to:
- Add files as attachments to a PDF
- List attachments in a PDF
- Extract attachments from a PDF
- Remove attachments from a PDF
- Use custom names and descriptions for attachments

## Scenario: Creating a Self-Contained Research Report

Imagine you've written a research report and want to distribute it with all the supporting data files. Instead of sending multiple files, you'll create a single PDF that contains everything.

## Step 1: Prepare Your Files

For this tutorial, let's assume you have:
- `research_report.pdf` - Your main report document
- `experiment_data.csv` - Raw experimental data
- `analysis_notes.txt` - Notes about your analysis
- `config.json` - Configuration used for analysis

If you don't have these files, you can create simple test files:

```bash
# Create a simple CSV file
echo "date,value
2024-01-01,10
2024-01-02,15
2024-01-03,12" > experiment_data.csv

# Create a notes file
echo "Analysis Notes
- Used baseline configuration
- Outliers removed from dataset
- Applied smoothing algorithm" > analysis_notes.txt

# Create a JSON config file
echo '{
  "algorithm": "linear_regression",
  "threshold": 0.85,
  "iterations": 1000
}' > config.json
```

## Step 2: Check for Existing Attachments

Before adding files, let's check if your PDF already has any attachments:

```bash
parxy attach:list research_report.pdf
```

You should see either:
```
No embedded files found in research_report.pdf
```

Or, if attachments exist:
```
Found 2 attached files in research_report.pdf:

⎿ old_data.csv
⎿ old_notes.txt
```

If you see existing attachments and want to start fresh, remove them:

```bash
parxy attach:remove research_report.pdf --all -o research_report.pdf
```

## Step 3: Add Your First Attachment

Let's start by adding the experiment data:

```bash
parxy attach:add research_report.pdf experiment_data.csv -o research_report_v2.pdf
```

You should see:
```
▣ Add attached files

Attaching 1 file...
⎿ Added experiment_data.csv (125 B)

Successfully added 1 attachment to research_report_v2.pdf
```

Now verify it was added:

```bash
parxy attach:list research_report_v2.pdf
```

Output:
```
Found 1 attached file in research_report_v2.pdf:

⎿ experiment_data.csv
```

## Step 4: Add Multiple Attachments with Descriptions

Now let's add the remaining files with helpful descriptions:

```bash
parxy attach:add research_report_v2.pdf \
  analysis_notes.txt \
  config.json \
  --description "Detailed analysis notes and methodology" \
  --description "Algorithm configuration and parameters" \
  -o research_report_complete.pdf
```

**Tip:** The backslashes (`\`) allow you to split a long command across multiple lines for readability.

## Step 5: Verify All Attachments

List the attachments with verbose output to see the descriptions:

```bash
parxy attach:list research_report_complete.pdf --verbose
```

You should see:
```
Found 3 attached files in research_report_complete.pdf:

⎿ experiment_data.csv (125 B)
⎿ analysis_notes.txt (156 B) - Detailed analysis notes and methodology
⎿ config.json (98 B) - Algorithm configuration and parameters
```

Notice that `experiment_data.csv` doesn't have a description because we added it separately.

## Step 6: Update an Attachment

Suppose you realize the data needs an update. Let's replace the experiment data with a new version:

First, create the updated data:

```bash
echo "date,value
2024-01-01,10
2024-01-02,15
2024-01-03,12
2024-01-04,18" > experiment_data_updated.csv
```

Now replace the old attachment:

```bash
parxy attach:add research_report_complete.pdf \
  experiment_data_updated.csv \
  --name experiment_data.csv \
  --description "Experimental data with additional measurements" \
  --overwrite \
  -o research_report_final.pdf
```

The `--name experiment_data.csv` tells Parxy to use this name in the PDF, and `--overwrite` allows replacing the existing file.

Verify the update:

```bash
parxy attach:list research_report_final.pdf -v
```

You should now see the updated description on the data file.

## Step 7: Extract an Attachment

Someone received your PDF and wants to work with the data. They can extract it:

```bash
parxy attach research_report_final.pdf experiment_data.csv
```

This creates `experiment_data.csv` in the current directory.

To save it somewhere specific:

```bash
parxy attach research_report_final.pdf experiment_data.csv -o ./extracted_data/data.csv
```

## Step 8: Quick View Text Files

For text files, you can quickly view the content without saving:

```bash
parxy attach research_report_final.pdf analysis_notes.txt --stdout
```

This prints the notes directly to your terminal:
```
Analysis Notes
- Used baseline configuration
- Outliers removed from dataset
- Applied smoothing algorithm
```

## Step 9: Remove Attachments

If you need to create a version without certain attachments:

```bash
parxy attach:remove research_report_final.pdf config.json -o research_report_public.pdf
```

This creates a version without the configuration file, perhaps for public distribution.

To remove all attachments:

```bash
parxy attach:remove research_report_final.pdf --all -o research_report_clean.pdf
```

You'll be asked to confirm:
```
This will remove the following attached files from research_report_final.pdf:
⎿ experiment_data.csv and 2 more

Continue? [y/N]:
```

Type `y` to proceed or `n` to cancel.

## Step 10: Organizing with Custom Names

Let's create a well-organized report with clear attachment names:

```bash
parxy attach:add research_report.pdf \
  experiment_data_updated.csv \
  analysis_notes.txt \
  config.json \
  --name "01_experiment_data.csv" \
  --name "02_analysis_notes.txt" \
  --name "03_configuration.json" \
  --description "Raw experimental measurements (updated 2024-01-04)" \
  --description "Methodology and analysis notes" \
  --description "Algorithm parameters and settings" \
  -o research_report_organized.pdf
```

Now when you list attachments:

```bash
parxy attach:list research_report_organized.pdf -v
```

You'll see:
```
Found 3 attached files in research_report_organized.pdf:

⎿ 01_experiment_data.csv (145 B) - Raw experimental measurements (updated 2024-01-04)
⎿ 02_analysis_notes.txt (156 B) - Methodology and analysis notes
⎿ 03_configuration.json (98 B) - Algorithm parameters and settings
```

The numbered prefixes make it clear what order to read them in!

## Best Practices Learned

From this tutorial, here are key best practices:

### 1. Use Descriptive Names
```bash
--name "2024_Q4_sales_data.csv"
```
Better than just `data.csv`

### 2. Add Helpful Descriptions
```bash
--description "Sales data for Q4 2024, filtered for North America region"
```
Helps others understand what the file contains

### 3. Organize with Prefixes
```bash
--name "01_data.csv" --name "02_code.py" --name "03_config.yaml"
```
Makes the reading order clear

### 4. Always Verify
```bash
parxy attach:list document.pdf -v
```
Check that attachments were added correctly

### 5. Use --overwrite Carefully
```bash
parxy attach:add doc.pdf new.csv --overwrite -o doc.pdf
```
Only when you're sure you want to replace

## Common Workflows

### Workflow 1: Bundle Data with Report

```bash
# Add all data files at once
parxy attach:add report.pdf data1.csv data2.csv data3.csv \
  --description "Dataset 1: Training data" \
  --description "Dataset 2: Validation data" \
  --description "Dataset 3: Test data" \
  -o report_with_data.pdf
```

### Workflow 2: Extract All Attachments

```bash
# Create extraction directory
mkdir extracted_files

# List attachments first
parxy attach:list document.pdf

# Extract each one
parxy attach document.pdf file1.csv -o extracted_files/file1.csv
parxy attach document.pdf file2.txt -o extracted_files/file2.txt
parxy attach document.pdf file3.json -o extracted_files/file3.json
```

### Workflow 3: Update Attachment

```bash
# Replace old version with new
parxy attach:add report.pdf updated_data.csv \
  --name data.csv \
  --description "Updated data as of 2024-01-15" \
  --overwrite \
  -o report.pdf
```

### Workflow 4: Clean Up Old Attachments

```bash
# Remove outdated files
parxy attach:remove report.pdf old_data_v1.csv old_data_v2.csv -o report.pdf

# Add current version
parxy attach:add report.pdf current_data.csv \
  --description "Latest dataset (2024-01-15)" \
  -o report_final.pdf
```

## Troubleshooting

### Problem: "Attachment already exists"

```bash
# Error: Attachment 'data.csv' already exists in document.pdf
```

**Solution:** Use `--overwrite` flag or remove the old attachment first:
```bash
parxy attach:add doc.pdf data.csv --overwrite -o doc.pdf
```

### Problem: "Cannot output binary file to stdout"

```bash
# Error when trying: parxy attach doc.pdf image.png --stdout
```

**Solution:** Binary files can't be displayed in terminal. Save to file instead:
```bash
parxy attach doc.pdf image.png -o image.png
```

### Problem: Wrong number of descriptions

```bash
# You have 3 files but provided 5 descriptions
```

**Solution:** Descriptions are matched by position. Provide matching counts or fewer:
```bash
parxy attach:add doc.pdf file1.csv file2.csv file3.csv \
  --description "First file" \
  --description "Second file" \
  --description "Third file" \
  -o doc.pdf
```

### Problem: Can't find attachment

```bash
# Error: Attachment 'data.xlsx' not found
# Available attachments: data.csv, notes.txt
```

**Solution:** Check spelling and list attachments to see exact names:
```bash
parxy attach:list document.pdf
```

## Next Steps

Now that you understand PDF attachments, you can:

1. **Explore other Parxy features:**
   - [PDF Manipulation](../howto/pdf_manipulation.md) - Merge and split PDFs
   - [Using the CLI](./using_cli.md) - Learn more CLI patterns

2. **Apply to your work:**
   - Bundle datasets with research papers
   - Attach source files to documentation
   - Create self-contained project packages
   - Archive related files together

3. **Automate with scripts:**
   - Create bash/shell scripts for repeated tasks
   - Integrate into your build pipeline
   - Automate report generation with data

## Summary

In this tutorial, you learned how to:
- ✅ Add single and multiple attachments to PDFs
- ✅ Use custom names and descriptions for clarity
- ✅ List and verify attachments
- ✅ Extract attachments for use
- ✅ Update and replace attachments
- ✅ Remove unwanted attachments
- ✅ Organize attachments with naming conventions

PDF attachments are a powerful way to create self-contained documents that include all necessary supporting files. Use them to make your work more accessible and easier to share!

## Quick Reference

```bash
# Add attachment with description
parxy attach:add report.pdf data.csv -d "Q4 Sales Data" -o report.pdf

# List all attachments with details
parxy attach:list document.pdf -v

# Extract attachment
parxy attach document.pdf data.csv -o ./data.csv

# Remove attachment
parxy attach:remove document.pdf old_data.csv -o cleaned.pdf

# View text attachment in terminal
parxy attach document.pdf notes.txt --stdout

# Replace attachment
parxy attach:add doc.pdf new.csv --name data.csv --overwrite -o doc.pdf
```

For more detailed information, see the [PDF Attachments How-To Guide](../howto/pdf_attachments.md).

"""PDF manipulation commands."""

import re
from pathlib import Path
from typing import List, Annotated, Optional, Tuple

import typer
import pymupdf

from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


def parse_input_with_pages(
    input_str: str,
) -> Tuple[str, Optional[int], Optional[int]]:
    """
    Parse input string to extract file path and page range.

    Supports formats:
    - file.pdf[1] - single page (1-based)
    - file.pdf[:2] - from start to page 2 (1-based, inclusive)
    - file.pdf[3:] - from page 3 to end (1-based)
    - file.pdf[3:5] - from page 3 to 5 (1-based, inclusive)
    - file.pdf - all pages

    Args:
        input_str: Input string with optional page range

    Returns:
        Tuple of (file_path, from_page, to_page) where pages are 0-based for PyMuPDF.
        from_page and to_page are None if no range specified or represent the range to use.
    """
    # Match pattern: filename[range]
    pattern = r'^(.+?)\[([^\]]+)\]$'
    match = re.match(pattern, input_str)

    if not match:
        # No page range specified
        return input_str, None, None

    file_path = match.group(1)
    page_range = match.group(2)

    # Parse the page range
    if ':' in page_range:
        # Range format [start:end]
        parts = page_range.split(':', 1)
        start_str = parts[0].strip()
        end_str = parts[1].strip()

        # Convert to 0-based indices
        # PyMuPDF uses 0-based indexing
        from_page = (int(start_str) - 1) if start_str else 0
        to_page = (int(end_str) - 1) if end_str else None  # None means last page

    else:
        # Single page [n]
        page_num = int(page_range) - 1  # Convert to 0-based
        from_page = page_num
        to_page = page_num

    return file_path, from_page, to_page


def collect_pdf_files_with_ranges(
    inputs: List[str],
) -> List[Tuple[Path, Optional[int], Optional[int]]]:
    """
    Collect PDF files from the input list with optional page ranges.

    For folders, only files in the exact directory are collected (non-recursive).
    For files with page ranges (e.g., file.pdf[1:3]), parse and extract the range.

    Args:
        inputs: List of file paths (with optional page ranges) and/or folder paths

    Returns:
        List of tuples: (Path, from_page, to_page) where pages are 0-based.
        from_page and to_page are None if all pages should be included.
    """
    files = []

    for input_str in inputs:
        # Parse the input to extract file path and page range
        file_path_str, from_page, to_page = parse_input_with_pages(input_str)
        path = Path(file_path_str)

        if path.is_file():
            # Check if it's a PDF
            if path.suffix.lower() == '.pdf':
                files.append((path, from_page, to_page))
            else:
                console.warning(f'Skipping non-PDF file: {file_path_str}')
        elif path.is_dir():
            # Non-recursive: only files in the given directory
            # Directories cannot have page ranges
            if from_page is not None or to_page is not None:
                console.warning(
                    f'Page ranges are not supported for directories: {input_str}'
                )
            pdf_files = sorted(path.glob('*.pdf'))
            if pdf_files:
                # Add all PDFs from directory without page ranges
                files.extend([(f, None, None) for f in pdf_files])
            else:
                console.warning(f'No PDF files found in directory: {file_path_str}')
        else:
            console.warning(f'Path not found: {file_path_str}')

    return files


@app.command(name='pdf:merge', help='Merge multiple PDF files into a single PDF')
def merge(
    inputs: Annotated[
        List[str],
        typer.Argument(
            help='One or more PDF files or folders to merge. Files support page ranges in square brackets (e.g., file.pdf[1:3]). Folders are processed non-recursively.',
        ),
    ],
    output: Annotated[
        str,
        typer.Option(
            '--output',
            '-o',
            help='Output file path for the merged PDF. If not specified, you will be prompted.',
        ),
    ] = None,
):
    """
    Merge multiple PDF files into a single PDF.

    Files are merged in the order they are provided. When a folder is specified,
    PDF files in that folder are included (non-recursively) and sorted alphabetically.

    Page ranges can be specified using square brackets with 1-based indexing:
    - file.pdf[1] - only page 1
    - file.pdf[:2] - from first page to page 2 (inclusive)
    - file.pdf[3:] - from page 3 to the end
    - file.pdf[3:5] - from page 3 to page 5 (inclusive)
    - file.pdf - all pages (no brackets)

    Examples:

        # Merge specific files with output specified
        parxy pdf:merge file1.pdf file2.pdf -o merged.pdf

        # Merge files - will prompt for output filename
        parxy pdf:merge file1.pdf file2.pdf

        # Merge with page ranges - take page 1 from file1, pages 2-4 from file2
        parxy pdf:merge file1.pdf[1] file2.pdf[2:4] -o merged.pdf

        # Merge specific pages from multiple files
        parxy pdf:merge doc1.pdf[:3] doc2.pdf[5:] doc3.pdf[2] -o combined.pdf

        # Mix full files and page ranges
        parxy pdf:merge cover.pdf report.pdf[1:10] appendix.pdf -o final.pdf

        # Merge all PDFs in a folder
        parxy pdf:merge /path/to/folder -o merged.pdf

        # Merge files and folders
        parxy pdf:merge doc1.pdf /path/to/folder doc2.pdf -o merged.pdf
    """
    console.action('Merge PDF files', space_after=False)

    # Collect all PDF files with page ranges
    files_with_ranges = collect_pdf_files_with_ranges(inputs)

    if not files_with_ranges:
        console.error('No PDF files found to merge.', panel=True)
        raise typer.Exit(1)

    if len(files_with_ranges) < 2:
        console.warning(
            'Only one PDF file found. At least two files are needed for merging.',
            panel=True,
        )
        raise typer.Exit(1)

    console.info(
        f'Found {len(files_with_ranges)} PDF file{"s" if len(files_with_ranges) > 1 else ""} to merge'
    )

    # Handle output path
    if output is None:
        output = typer.prompt('Enter output filename or path')

    output_path = Path(output)

    # If only a filename is provided (not an absolute path), use the first input file's directory
    if not output_path.is_absolute() and output_path.parent == Path('.'):
        first_file = files_with_ranges[0][0]
        output_path = first_file.parent / output_path

    # Ensure the output has .pdf extension
    if output_path.suffix.lower() != '.pdf':
        output_path = output_path.with_suffix('.pdf')

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Merge PDFs
    try:
        with console.shimmer(f'Merging {len(files_with_ranges)} PDF files...'):
            merged_pdf = pymupdf.open()

            for file_path, from_page, to_page in files_with_ranges:
                try:
                    pdf = pymupdf.open(file_path)

                    # Determine page range to insert
                    if from_page is None and to_page is None:
                        # Insert all pages
                        page_info = 'all pages'
                        merged_pdf.insert_pdf(pdf)
                    else:
                        # Insert specific page range
                        # PyMuPDF insert_pdf uses from_page and to_page (inclusive, 0-based)
                        actual_from = from_page if from_page is not None else 0
                        actual_to = to_page if to_page is not None else (len(pdf) - 1)

                        # Validate page range
                        if actual_from < 0 or actual_from >= len(pdf):
                            console.warning(
                                f'Invalid page range for {file_path.name}: page {actual_from + 1} does not exist'
                            )
                            pdf.close()
                            continue

                        if actual_to < 0 or actual_to >= len(pdf):
                            console.warning(
                                f'Invalid page range for {file_path.name}: page {actual_to + 1} does not exist'
                            )
                            pdf.close()
                            continue

                        if actual_from > actual_to:
                            console.warning(
                                f'Invalid page range for {file_path.name}: start page {actual_from + 1} > end page {actual_to + 1}'
                            )
                            pdf.close()
                            continue

                        # Format page info for display (1-based)
                        if actual_from == actual_to:
                            page_info = f'page {actual_from + 1}'
                        else:
                            page_info = f'pages {actual_from + 1}-{actual_to + 1}'

                        merged_pdf.insert_pdf(
                            pdf, from_page=actual_from, to_page=actual_to
                        )

                    console.print(
                        f'[faint]⎿ [/faint] Adding {file_path.name} ({page_info})'
                    )
                    pdf.close()

                except Exception as e:
                    console.error(f'Error processing {file_path.name}: {str(e)}')
                    merged_pdf.close()
                    raise typer.Exit(1)

            # Save the merged PDF
            merged_pdf.save(str(output_path))
            merged_pdf.close()

        console.newline()
        console.success(
            f'Successfully merged {len(files_with_ranges)} files into {output_path}'
        )

    except Exception as e:
        console.error(f'Error during merge: {str(e)}')
        raise typer.Exit(1)

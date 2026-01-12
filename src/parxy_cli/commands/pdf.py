"""PDF manipulation commands."""

from pathlib import Path
from typing import List, Annotated, Optional

import typer

from parxy_cli.console.console import Console
from parxy_cli.services import PdfService, collect_pdf_files_with_ranges

app = typer.Typer()

console = Console()


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

    # Merge PDFs using service
    try:
        with console.shimmer(f'Merging {len(files_with_ranges)} PDF files...'):
            # Display progress for each file
            for file_path, from_page, to_page in files_with_ranges:
                # Determine page range info for display
                if from_page is None and to_page is None:
                    page_info = 'all pages'
                else:
                    actual_from = from_page if from_page is not None else 0
                    actual_to = to_page if to_page is not None else 'end'

                    if from_page == to_page:
                        page_info = f'page {from_page + 1}'
                    elif to_page is None:
                        page_info = f'pages {actual_from + 1}-end'
                    else:
                        page_info = f'pages {actual_from + 1}-{to_page + 1}'

                console.print(
                    f'[faint]⎿ [/faint] Adding {file_path.name} ({page_info})'
                )

            # Use service to merge PDFs
            PdfService.merge_pdfs(files_with_ranges, output_path)

        console.newline()
        console.success(
            f'Successfully merged {len(files_with_ranges)} files into {output_path}'
        )

    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error during merge: {str(e)}')
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error during merge: {str(e)}')
        raise typer.Exit(1)


@app.command(name='pdf:split', help='Split a PDF file into individual pages')
def split(
    input_file: Annotated[
        str,
        typer.Argument(
            help='PDF file to split',
        ),
    ],
    output_dir: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output directory for split files. If not specified, creates a folder next to the input file.',
        ),
    ] = None,
    prefix: Annotated[
        Optional[str],
        typer.Option(
            '--prefix',
            '-p',
            help='Prefix for output filenames. If not specified, uses the input filename.',
        ),
    ] = None,
):
    """
    Split a PDF file into individual pages.

    Each page becomes a separate PDF file in the output directory.

    Output files are named: {prefix}_page_{number}.pdf

    Examples:

        # Split into individual pages (default behavior)
        parxy pdf:split document.pdf

        # Split with custom output directory
        parxy pdf:split document.pdf -o /path/to/output

        # Split with custom prefix
        parxy pdf:split document.pdf --prefix chapter

        # Split with custom output and prefix
        parxy pdf:split report.pdf -o ./pages -p page
    """
    console.action('Split PDF file', space_after=False)

    # Validate input file
    input_path = Path(input_file)
    if not input_path.is_file():
        console.error(f'Input file not found: {input_file}', panel=True)
        raise typer.Exit(1)

    if input_path.suffix.lower() != '.pdf':
        console.error(f'Input file must be a PDF: {input_file}', panel=True)
        raise typer.Exit(1)

    # Determine output directory
    if output_dir is None:
        # Create a folder next to the input file
        output_path = input_path.parent / f'{input_path.stem}_split'
    else:
        output_path = Path(output_dir)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Determine filename prefix
    if prefix is None:
        prefix = input_path.stem

    # Split PDF using service
    try:
        # Get page count first to display info
        import pymupdf

        pdf = pymupdf.open(input_path)
        total_pages = len(pdf)
        pdf.close()

        if total_pages == 0:
            console.error('PDF file is empty (no pages)', panel=True)
            raise typer.Exit(1)

        console.info(
            f'Processing PDF with {total_pages} page{"s" if total_pages > 1 else ""}'
        )
        console.info(
            f'Splitting into {total_pages} file{"s" if total_pages > 1 else ""}'
        )

        with console.shimmer(f'Splitting PDF...'):
            # Use service to split PDF
            output_files = PdfService.split_pdf(input_path, output_path, prefix)

            # Display created files
            for idx, output_file in enumerate(output_files):
                console.print(
                    f'[faint]⎿ [/faint] Created {output_file.name} (page {idx + 1})'
                )

        console.newline()
        console.success(
            f'Successfully split PDF into {len(output_files)} file{"s" if len(output_files) > 1 else ""} in {output_path}'
        )

    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error during split: {str(e)}')
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error during split: {str(e)}')
        raise typer.Exit(1)

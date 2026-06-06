"""PDF manipulation commands."""

import json
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
            help='Output path. Without --combine: output directory for split files (default: folder next to input). With --combine: output file path (default: {stem}_pages_{from}-{to}.pdf next to input).',
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
    pages: Annotated[
        Optional[str],
        typer.Option(
            '--pages',
            help='Page range to extract (1-based). Examples: "1" (single page), "1:3" (pages 1-3), ":3" (up to page 3), "3:" (from page 3). If not specified, all pages are extracted.',
        ),
    ] = None,
    combine: Annotated[
        bool,
        typer.Option(
            '--combine',
            help='Combine extracted pages into a single PDF instead of one file per page.',
        ),
    ] = False,
    every: Annotated[
        Optional[int],
        typer.Option(
            '--every',
            '-e',
            help='Split into chunks of N pages each. Cannot be used with --combine.',
        ),
    ] = None,
):
    """
    Split a PDF file into individual pages.

    Each page becomes a separate PDF file in the output directory.

    Output files are named: {prefix}_page_{number}.pdf

    Page ranges use 1-based indexing:
    - "1"   - only page 1
    - "1:3" - pages 1 to 3 (inclusive)
    - ":3"  - from first page to page 3
    - "3:"  - from page 3 to the end

    Examples:

        # Split into individual pages (default behavior)
        parxy pdf:split document.pdf

        # Split with custom output directory
        parxy pdf:split document.pdf -o /path/to/output

        # Split with custom prefix
        parxy pdf:split document.pdf --prefix chapter

        # Split with custom output and prefix
        parxy pdf:split report.pdf -o ./pages -p page

        # Extract only pages 2 to 5
        parxy pdf:split document.pdf --pages 2:5

        # Extract a single page
        parxy pdf:split document.pdf --pages 3

        # Combine pages 2-5 into a single PDF
        parxy pdf:split document.pdf --pages 2:5 --combine

        # Combine with custom output path
        parxy pdf:split document.pdf --pages 2:5 --combine -o extracted.pdf

        # Split into chunks of 10 pages each
        parxy pdf:split document.pdf --every 10

        # Split into chunks of 5 pages, only from pages 3-20
        parxy pdf:split document.pdf --every 5 --pages 3:20
    """
    console.action('Split PDF file', space_after=False)

    # Validate mutually exclusive options
    if every is not None and combine:
        console.error('--every and --combine cannot be used together.', panel=True)
        raise typer.Exit(1)

    if every is not None and every < 1:
        console.error('--every must be a positive integer.', panel=True)
        raise typer.Exit(1)

    # Validate input file
    input_path = Path(input_file)
    if not input_path.is_file():
        console.error(f'Input file not found: {input_file}', panel=True)
        raise typer.Exit(1)

    if input_path.suffix.lower() != '.pdf':
        console.error(f'Input file must be a PDF: {input_file}', panel=True)
        raise typer.Exit(1)

    # Parse --pages option into 0-based from_page / to_page
    from_page = None
    to_page = None
    if pages is not None:
        try:
            if ':' in pages:
                start_str, end_str = pages.split(':', 1)
                from_page = (int(start_str) - 1) if start_str.strip() else None
                to_page = (int(end_str) - 1) if end_str.strip() else None
            else:
                page_num = int(pages) - 1
                from_page = page_num
                to_page = page_num
        except ValueError:
            console.error(
                f'Invalid --pages value: "{pages}". Use formats like "1", "1:3", ":3", or "3:".',
                panel=True,
            )
            raise typer.Exit(1)

    # Determine output directory (only relevant when not combining)
    if not combine:
        if output_dir is None:
            output_path = input_path.parent / f'{input_path.stem}_split'
        else:
            output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = None  # unused in combine mode

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

        # Determine effective range for display
        effective_from = (from_page if from_page is not None else 0) + 1
        effective_to = (to_page if to_page is not None else total_pages - 1) + 1
        extract_count = effective_to - effective_from + 1

        console.info(
            f'Processing PDF with {total_pages} page{"s" if total_pages > 1 else ""}'
        )
        if pages is not None:
            console.info(
                f'Extracting pages {effective_from}-{effective_to} ({extract_count} page{"s" if extract_count > 1 else ""})'
            )

        if every is not None:
            # Determine output directory
            if output_dir is None:
                output_path = input_path.parent / f'{input_path.stem}_split'
            else:
                output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            chunk_count = (extract_count + every - 1) // every
            console.info(
                f'Splitting into {chunk_count} chunk{"s" if chunk_count > 1 else ""} of up to {every} page{"s" if every > 1 else ""} each'
            )

            with console.shimmer('Splitting PDF into chunks...'):
                output_files = PdfService.split_pdf_by_chunk(
                    input_path, output_path, prefix, every, from_page, to_page
                )

                for output_file in output_files:
                    console.print(f'[faint]⎿ [/faint] Created {output_file.name}')

            console.newline()
            console.success(
                f'Successfully split PDF into {len(output_files)} chunk{"s" if len(output_files) > 1 else ""} in {output_path}'
            )

        elif combine:
            # Determine output file path
            if output_dir is not None:
                combined_output = Path(output_dir)
                if combined_output.suffix.lower() != '.pdf':
                    combined_output = combined_output.with_suffix('.pdf')
            else:
                range_label = (
                    f'{effective_from}-{effective_to}'
                    if effective_from != effective_to
                    else str(effective_from)
                )
                combined_output = (
                    input_path.parent / f'{input_path.stem}_pages_{range_label}.pdf'
                )

            with console.shimmer('Extracting pages into single PDF...'):
                PdfService.extract_pages(
                    input_path, combined_output, from_page, to_page
                )

            console.newline()
            console.success(
                f'Successfully extracted {extract_count} page{"s" if extract_count > 1 else ""} into {combined_output}'
            )
        else:
            console.info(
                f'Splitting into {extract_count} file{"s" if extract_count > 1 else ""}'
            )

            with console.shimmer('Splitting PDF...'):
                output_files = PdfService.split_pdf(
                    input_path, output_path, prefix, from_page, to_page
                )

                for output_file in output_files:
                    page_num = int(output_file.stem.rsplit('_', 1)[-1])
                    console.print(
                        f'[faint]⎿ [/faint] Created {output_file.name} (page {page_num})'
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


@app.command(
    name='pdf:split-by-text',
    help='Split a PDF into chunks whenever a page matches a text condition',
)
def split_by_text(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to split'),
    ],
    text: Annotated[
        List[str],
        typer.Option(
            '--text',
            '-t',
            help='Text to match. Can be repeated for multiple patterns (OR logic).',
        ),
    ] = None,
    mode: Annotated[
        str,
        typer.Option(
            '--mode',
            '-m',
            help='Matching mode: "contains" (default) or "starts-with".',
        ),
    ] = 'contains',
    ignore_case: Annotated[
        bool,
        typer.Option(
            '--ignore-case',
            '-i',
            help='Case-insensitive matching.',
        ),
    ] = False,
    regex: Annotated[
        bool,
        typer.Option(
            '--regex',
            help='Treat --text values as regular expressions.',
        ),
    ] = False,
    discard_preamble: Annotated[
        bool,
        typer.Option(
            '--discard-preamble',
            help='Discard pages that appear before the first matching page.',
        ),
    ] = False,
    output_dir: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output directory for chunk files (default: {stem}_split next to input).',
        ),
    ] = None,
    prefix: Annotated[
        Optional[str],
        typer.Option(
            '--prefix',
            '-p',
            help='Prefix for output filenames. Defaults to the input filename stem.',
        ),
    ] = None,
):
    """
    Split a PDF into chunks whenever a page matches a text condition.

    A new chunk begins at each page that satisfies the match condition. Pages
    before the first match are included as a leading chunk unless
    --discard-preamble is given.

    Matching modes:
      contains    - page text contains the pattern anywhere (default)
      starts-with - page text starts with the pattern (after leading whitespace)

    Multiple --text values are combined with OR logic: any match triggers a split.
    Use --regex to treat --text values as regular expressions.

    Output files are named: {prefix}_part_{N}_{pages}.pdf

    Examples:

        # Split whenever a page contains "Chapter"
        parxy pdf:split-by-text document.pdf --text "Chapter"

        # Split on "Invoice" or "Credit Note", case-insensitive
        parxy pdf:split-by-text document.pdf -t "Invoice" -t "Credit Note" -i

        # Split when a page starts with "SECTION"
        parxy pdf:split-by-text document.pdf --text "SECTION" --mode starts-with

        # Split using a regex pattern (e.g. "Chapter N" headings)
        parxy pdf:split-by-text document.pdf --text "^Chapter \\d+" --regex

        # Discard pages before the first match and write to a custom directory
        parxy pdf:split-by-text document.pdf -t "Invoice" --discard-preamble -o ./invoices
    """
    console.action('Split PDF by text condition', space_after=False)

    if not text:
        console.error('At least one --text pattern is required.', panel=True)
        raise typer.Exit(1)

    if mode not in ('contains', 'starts-with'):
        console.error(
            f'Invalid --mode "{mode}". Choose "contains" or "starts-with".', panel=True
        )
        raise typer.Exit(1)

    input_path = Path(input_file)
    if not input_path.is_file():
        console.error(f'Input file not found: {input_file}', panel=True)
        raise typer.Exit(1)

    if input_path.suffix.lower() != '.pdf':
        console.error(f'Input file must be a PDF: {input_file}', panel=True)
        raise typer.Exit(1)

    if output_dir is None:
        out_path = input_path.parent / f'{input_path.stem}_split'
    else:
        out_path = Path(output_dir)

    if prefix is None:
        prefix = input_path.stem

    # Display matching configuration
    mode_label = 'starts with' if mode == 'starts-with' else 'contains'
    pattern_list = ', '.join(f'"{p}"' for p in text)
    console.info(f'Patterns ({mode_label}): {pattern_list}')
    if ignore_case:
        console.info('Case-insensitive matching enabled')
    if regex:
        console.info('Regex matching enabled')

    try:
        with console.shimmer('Scanning pages and splitting PDF...'):
            chunks = PdfService.split_pdf_by_text(
                input_path,
                out_path,
                prefix,
                patterns=text,
                mode=mode,
                ignore_case=ignore_case,
                use_regex=regex,
                discard_before_first_match=discard_preamble,
            )

            for output_file, first_page, last_page in chunks:
                page_label = (
                    f'page {first_page}'
                    if first_page == last_page
                    else f'pages {first_page}-{last_page}'
                )
                console.print(
                    f'[faint]⎿ [/faint] Created {output_file.name} ({page_label})'
                )

        console.newline()
        console.success(
            f'Successfully split PDF into {len(chunks)} chunk{"s" if len(chunks) > 1 else ""} in {out_path}'
        )

    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error during split: {str(e)}')
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error during split: {str(e)}')
        raise typer.Exit(1)


def _validate_pdf_input(input_file: str) -> Path:
    """Validate that input_file is an existing .pdf file and return its Path."""
    input_path = Path(input_file)
    if not input_path.is_file():
        console.error(f'Input file not found: {input_file}', panel=True)
        raise typer.Exit(1)
    if input_path.suffix.lower() != '.pdf':
        console.error(f'Input file must be a PDF: {input_file}', panel=True)
        raise typer.Exit(1)
    return input_path


@app.command(
    name='pdf:tags-check',
    help='Check whether a PDF is a tagged (accessible) PDF',
)
def tags_check(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to inspect'),
    ],
    as_json: Annotated[
        bool,
        typer.Option(
            '--json',
            help='Output the detection result as JSON.',
        ),
    ] = False,
):
    """
    Check whether a PDF is a tagged (accessible) PDF.

    A PDF is considered tagged when its catalog marks the content as tagged
    (/MarkInfo /Marked true) and provides a logical structure tree
    (/StructTreeRoot). The command also reports the declared document language
    and how many structure elements the tree contains.

    The process exits with code 0 when the PDF is tagged and 2 when it is not,
    so it can be used in scripts.

    Examples:

        # Human-readable report
        parxy pdf:tags-check document.pdf

        # Machine-readable output
        parxy pdf:tags-check document.pdf --json
    """
    input_path = _validate_pdf_input(input_file)

    try:
        info = PdfService.is_tagged(input_path)
    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error inspecting PDF: {str(e)}')
        raise typer.Exit(1)

    if as_json:
        # Plain stdout (not rich) so the JSON is emitted verbatim, without
        # markup interpretation of brackets or width-based line wrapping.
        typer.echo(json.dumps(info, indent=2))
        raise typer.Exit(0 if info['tagged'] else 2)

    console.action('Check tagged PDF', space_after=False)
    console.info(f'File: {input_path.name}')

    if info['tagged']:
        console.success('This is a tagged PDF')
    else:
        console.warning('This is NOT a tagged PDF')

    marked = '✓' if info['marked'] else '✗'
    struct = '✓' if info['has_struct_tree'] else '✗'
    console.print(f'[faint]⎿ [/faint] Marked content (/MarkInfo): {marked}')
    console.print(f'[faint]⎿ [/faint] Structure tree (/StructTreeRoot): {struct}')
    console.print(
        f'[faint]⎿ [/faint] Structure elements: {info["struct_element_count"]}'
    )
    console.print(f'[faint]⎿ [/faint] Language (/Lang): {info["lang"] or "not set"}')
    console.print(f'[faint]⎿ [/faint] Pages: {info["page_count"]}')

    raise typer.Exit(0 if info['tagged'] else 2)


@app.command(
    name='pdf:tags',
    help='Extract the tag (structure) tree of a tagged PDF',
)
def tags(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to inspect'),
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Write the extracted tags as JSON to this file instead of printing a tree.',
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            '--json',
            help='Print the extracted tags as JSON to stdout.',
        ),
    ] = False,
    with_text: Annotated[
        bool,
        typer.Option(
            '--text',
            help='Include the text content of each element. Rebuilds the tree '
            'per page; accessibility attributes (alt text, page refs) are not '
            'shown in this mode.',
        ),
    ] = False,
):
    """
    Extract the logical structure (tag) tree of a tagged PDF.

    By default this walks the /StructTreeRoot and prints each structure
    element, the page it refers to, and any alternative text, title, or
    language attached to it. This view spans the whole document but does not
    include body text (which lives in the page content streams).

    Use --text to instead reconstruct the structure per page including the
    visible text of each element (P, Strong, Span, ...). That view shows text
    but not the alt-text / page-reference accessibility attributes.

    Use --json (stdout) or --output (file) to obtain the full nested structure
    for further processing.

    Examples:

        # Print the tag tree (accessibility view)
        parxy pdf:tags document.pdf

        # Include the text content of each element
        parxy pdf:tags document.pdf --text

        # Emit JSON to stdout
        parxy pdf:tags document.pdf --json

        # Save the tag tree to a file
        parxy pdf:tags document.pdf -o tags.json
    """
    input_path = _validate_pdf_input(input_file)

    try:
        if with_text:
            result = PdfService.extract_tags_with_text(input_path)
        else:
            result = PdfService.extract_tags(input_path)
    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error extracting tags: {str(e)}')
        raise typer.Exit(1)

    if output is not None:
        output_path = Path(output)
        if output_path.suffix.lower() != '.json':
            output_path = output_path.with_suffix('.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        console.success(f'Saved tag tree to {output_path}')
        return

    if as_json:
        # Plain stdout (not rich) so the JSON is emitted verbatim, without
        # markup interpretation of brackets or width-based line wrapping.
        typer.echo(json.dumps(result, indent=2))
        return

    console.action('Extract PDF tags', space_after=False)

    if not result['tagged']:
        console.warning('No structure tree found — this PDF is not tagged.', panel=True)
        raise typer.Exit(2)

    from rich.tree import Tree

    if with_text:
        _render_text_tags(input_path, result)
        return

    def _label(node: dict) -> str:
        parts = [f'[highlight]{node["type"]}[/highlight]']
        if node['page'] is not None:
            parts.append(f'[faint](page {node["page"]})[/faint]')
        if node['title']:
            parts.append(f'[muted]"{node["title"]}"[/muted]')
        if node['alt']:
            parts.append(f'[cyan]alt: {node["alt"]}[/cyan]')
        if node['lang']:
            parts.append(f'[faint]lang={node["lang"]}[/faint]')
        return ' '.join(parts)

    def _add(parent_tree, node: dict):
        branch = parent_tree.add(_label(node))
        for child in node['children']:
            _add(branch, child)

    tree = Tree(f'[bold]{input_path.name}[/bold]')
    for root in result['roots']:
        _add(tree, root)
    console.console.print(tree)

    console.newline()
    summary = ', '.join(
        f'{count}×{tag}' for tag, count in sorted(result['tag_counts'].items())
    )
    total = sum(result['tag_counts'].values())
    console.info(f'{total} structure elements: {summary}')


def _render_text_tags(input_path: Path, result: dict):
    """Render the per-page, text-bearing tag tree produced with --text."""
    from rich.markup import escape
    from rich.tree import Tree

    def _truncate(text: str, limit: int = 100) -> str:
        text = ' '.join(text.split())
        return text if len(text) <= limit else text[: limit - 1] + '…'

    def _type_label(node: dict) -> str:
        label = f'[highlight]{node["type"]}[/highlight]'
        if node['standard_type'] and node['standard_type'] != node['type']:
            label += f' [faint]({node["standard_type"]})[/faint]'
        return label

    def _add(parent_tree, node: dict):
        if node['type'] is None:
            # Bare text run
            parent_tree.add(f'[muted]"{escape(_truncate(node["text"]))}"[/muted]')
            return
        children = node['children']
        # Inline a single text-only child next to its element type
        if len(children) == 1 and children[0]['type'] is None:
            text = escape(_truncate(children[0]['text']))
            parent_tree.add(f'{_type_label(node)}  [muted]"{text}"[/muted]')
            return
        branch = parent_tree.add(_type_label(node))
        for child in children:
            _add(branch, child)

    multi_page = result['page_count'] > 1
    for page in result['pages']:
        title = (
            f'[bold]{input_path.name}[/bold] [faint]— page {page["page"]}[/faint]'
            if multi_page
            else f'[bold]{input_path.name}[/bold]'
        )
        tree = Tree(title)
        for root in page['roots']:
            _add(tree, root)
        console.console.print(tree)

    console.newline()
    console.info(
        f'{result["page_count"]} page{"s" if result["page_count"] > 1 else ""} '
        '(per-page reconstruction with text)'
    )


@app.command(
    name='pdf:tag-skeleton',
    help='Copy a tagged PDF keeping its tags but removing visible content',
)
def tag_skeleton(
    input_file: Annotated[
        str,
        typer.Argument(help='Tagged PDF file to strip'),
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output path for the tags-only PDF (default: {stem}_tags.pdf next to input).',
        ),
    ] = None,
):
    """
    Copy a tagged PDF, keeping the tag tree but removing visible content.

    Every page's content streams and resources (text, images, fonts) are
    removed while the page objects and the /StructTreeRoot logical structure
    are preserved. The result is a lightweight document that still carries the
    accessibility structure, useful for inspecting or testing the tag tree in
    isolation.

    Examples:

        # Strip content, write {stem}_tags.pdf next to the input
        parxy pdf:tag-skeleton document.pdf

        # Strip content to a specific path
        parxy pdf:tag-skeleton document.pdf -o tags-only.pdf
    """
    input_path = _validate_pdf_input(input_file)

    if output is None:
        output_path = input_path.parent / f'{input_path.stem}_tags.pdf'
    else:
        output_path = Path(output)
        if output_path.suffix.lower() != '.pdf':
            output_path = output_path.with_suffix('.pdf')

    console.action('Strip PDF to tags', space_after=False)

    try:
        with console.shimmer('Removing content while preserving tags...'):
            result = PdfService.strip_to_tags(input_path, output_path)
    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error during strip: {str(e)}')
        raise typer.Exit(1)

    if not result['tagged']:
        console.warning(
            'Source PDF has no structure tree — the output will have no tags.'
        )

    saved = result['original_size'] - result['stripped_size']
    console.newline()
    console.success(f'Wrote tags-only PDF to {output_path}')
    console.print(
        f'[faint]⎿ [/faint] Structure elements preserved: {result["struct_element_count"]}'
    )
    console.print(
        f'[faint]⎿ [/faint] Size: {result["original_size"]:,} → {result["stripped_size"]:,} bytes '
        f'(−{saved:,})'
    )


@app.command(
    name='pdf:tag-template',
    help='Create an empty tagged PDF skeleton for accessibility work',
)
def tag_template(
    output: Annotated[
        str,
        typer.Option(
            '--output',
            '-o',
            help='Output file path for the template PDF. If not specified, you will be prompted.',
        ),
    ] = None,
    pages: Annotated[
        int,
        typer.Option(
            '--pages',
            help='Number of blank pages to create (default: 1).',
        ),
    ] = 1,
    lang: Annotated[
        str,
        typer.Option(
            '--lang',
            help='Document language tag set on the catalog (default: en-US).',
        ),
    ] = 'en-US',
    title: Annotated[
        Optional[str],
        typer.Option(
            '--title',
            help='Optional document title stored in the PDF metadata.',
        ),
    ] = None,
):
    """
    Create an empty tagged PDF skeleton for accessibility work.

    Generates a fresh PDF with the requested number of blank pages and a valid
    logical structure tree: the content is marked as tagged (/MarkInfo /Marked
    true) and a /StructTreeRoot groups one paragraph (/P) structure element per
    page under a /Document element. A starting point for building or testing
    accessible PDFs.

    Examples:

        # Single-page template
        parxy pdf:tag-template -o template.pdf

        # Three-page German template with a title
        parxy pdf:tag-template -o template.pdf --pages 3 --lang de-DE --title "Report"
    """
    console.action('Create tagged PDF template', space_after=False)

    if pages < 1:
        console.error('--pages must be a positive integer.', panel=True)
        raise typer.Exit(1)

    if output is None:
        output = typer.prompt('Enter output filename or path')

    output_path = Path(output)
    if output_path.suffix.lower() != '.pdf':
        output_path = output_path.with_suffix('.pdf')

    try:
        with console.shimmer('Building tagged PDF skeleton...'):
            PdfService.create_tag_template(
                output_path, pages=pages, lang=lang, title=title
            )
    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error creating template: {str(e)}')
        raise typer.Exit(1)

    console.newline()
    console.success(f'Created tagged PDF template at {output_path}')
    console.print(
        f'[faint]⎿ [/faint] {pages} page{"s" if pages > 1 else ""}, language {lang}'
    )


@app.command(
    name='pdf:outline',
    help='Print or export the outline (bookmarks / table of contents) of a PDF',
)
def outline(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to inspect'),
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Write the outline as JSON to this file instead of printing a tree.',
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            '--json',
            help='Print the outline as JSON to stdout.',
        ),
    ] = False,
    flat: Annotated[
        bool,
        typer.Option(
            '--flat',
            help='Print a flat, indented list instead of a tree.',
        ),
    ] = False,
):
    """
    Print or export the outline (bookmarks / table of contents) of a PDF.

    Reads the PDF's bookmark hierarchy and shows each entry with the page it
    points to. By default a nested tree is rendered; use --flat for a plain
    indented list, or --json / --output to obtain the structured data (both a
    flat list of entries and the nested tree) for further processing.

    Examples:

        # Render the outline as a tree
        parxy pdf:outline document.pdf

        # Flat, indented listing
        parxy pdf:outline document.pdf --flat

        # Emit JSON to stdout
        parxy pdf:outline document.pdf --json

        # Save the outline to a file
        parxy pdf:outline document.pdf -o outline.json
    """
    input_path = _validate_pdf_input(input_file)

    try:
        result = PdfService.extract_outline(input_path)
    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error extracting outline: {str(e)}')
        raise typer.Exit(1)

    if output is not None:
        output_path = Path(output)
        if output_path.suffix.lower() != '.json':
            output_path = output_path.with_suffix('.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        console.success(f'Saved outline to {output_path}')
        return

    if as_json:
        # Plain stdout (not rich) so the JSON is emitted verbatim, without
        # markup interpretation of brackets or width-based line wrapping.
        typer.echo(json.dumps(result, indent=2))
        return

    console.action('Extract PDF outline', space_after=False)

    if not result['has_outline']:
        console.warning('This PDF has no outline (no bookmarks).', panel=True)
        raise typer.Exit(2)

    from rich.markup import escape

    def _page_suffix(page: Optional[int]) -> str:
        return f' [faint](page {page})[/faint]' if page is not None else ''

    if flat:
        for entry in result['entries']:
            indent = '  ' * (entry['level'] - 1)
            console.print(
                f'{indent}[highlight]{escape(entry["title"])}[/highlight]'
                f'{_page_suffix(entry["page"])}'
            )
    else:
        from rich.tree import Tree

        def _add(parent_tree, node: dict):
            branch = parent_tree.add(
                f'[highlight]{escape(node["title"])}[/highlight]'
                f'{_page_suffix(node["page"])}'
            )
            for child in node['children']:
                _add(branch, child)

        tree = Tree(f'[bold]{input_path.name}[/bold]')
        for node in result['tree']:
            _add(tree, node)
        console.console.print(tree)

    console.newline()
    console.info(
        f'{result["entry_count"]} bookmark'
        f'{"s" if result["entry_count"] != 1 else ""} '
        f'across {result["page_count"]} page'
        f'{"s" if result["page_count"] != 1 else ""}'
    )


@app.command(
    name='pdf:xmp',
    help='Read and extract the XMP metadata of a PDF',
)
def xmp(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to inspect'),
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Write the metadata to this file. A .xml extension writes the '
            'raw XMP packet; any other extension writes parsed JSON.',
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            '--json',
            help='Print the parsed metadata as JSON to stdout.',
        ),
    ] = False,
    raw: Annotated[
        bool,
        typer.Option(
            '--raw',
            help='Print the raw XMP XML packet to stdout.',
        ),
    ] = False,
):
    """
    Read and extract the XMP metadata packet of a PDF.

    XMP is an RDF/XML metadata packet embedded in the document. By default the
    parsed properties (such as dc:title, dc:creator, pdf:Producer,
    xmp:CreateDate) are printed alongside the classic /Info dictionary. Use
    --raw to print the original XML packet, or --json / --output for structured
    data. Writing to a path ending in .xml exports the raw packet.

    Examples:

        # Print parsed XMP properties
        parxy pdf:xmp document.pdf

        # Print the raw XMP XML packet
        parxy pdf:xmp document.pdf --raw

        # Emit parsed metadata as JSON
        parxy pdf:xmp document.pdf --json

        # Save the raw XMP packet to a file
        parxy pdf:xmp document.pdf -o metadata.xml

        # Save parsed metadata as JSON
        parxy pdf:xmp document.pdf -o metadata.json
    """
    input_path = _validate_pdf_input(input_file)

    try:
        result = PdfService.extract_xmp_metadata(input_path)
    except (ValueError, FileNotFoundError) as e:
        console.error(f'Error extracting XMP metadata: {str(e)}')
        raise typer.Exit(1)

    if output is not None:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() == '.xml':
            if not result['has_xmp']:
                console.warning('This PDF has no XMP metadata packet to export.')
                raise typer.Exit(2)
            output_path.write_text(result['raw'], encoding='utf-8')
            console.success(f'Saved raw XMP packet to {output_path}')
        else:
            if output_path.suffix.lower() != '.json':
                output_path = output_path.with_suffix('.json')
            output_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
            console.success(f'Saved XMP metadata to {output_path}')
        return

    if as_json:
        # Plain stdout (not rich) so the JSON is emitted verbatim, without
        # markup interpretation of brackets or width-based line wrapping.
        typer.echo(json.dumps(result, indent=2))
        return

    if raw:
        if not result['has_xmp']:
            console.warning('This PDF has no XMP metadata packet.', panel=True)
            raise typer.Exit(2)
        typer.echo(result['raw'])
        return

    from rich.markup import escape

    console.action('Extract PDF XMP metadata', space_after=False)

    if not result['has_xmp']:
        console.warning('This PDF has no XMP metadata packet.', panel=True)
    else:
        if result['properties']:
            for key, value in result['properties'].items():
                shown = ', '.join(value) if isinstance(value, list) else value
                console.print(
                    f'[highlight]{escape(key)}[/highlight]: '
                    f'[muted]{escape(str(shown))}[/muted]'
                )
        else:
            console.info('XMP packet present but no recognised properties.')

    if result['doc_info']:
        console.newline()
        console.info('Document info (/Info):')
        for key, value in result['doc_info'].items():
            if value:
                console.print(
                    f'[faint]⎿ [/faint] {escape(str(key))}: '
                    f'[muted]{escape(str(value))}[/muted]'
                )

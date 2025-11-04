"""Command line interface for Parxy document processing."""

import os
import sys
import time
from typing import Optional, List, Annotated


import typer
from rich.layout import Layout
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown

from parxy_core.facade import Parxy
from parxy_core.models.models import Document, TextBlock, Metadata

from parxy_cli.models import Level, OutputMode
from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


def extract_toc(doc: Document) -> List[dict]:
    """
    Extract table of contents from document headings.

    Args:
        doc: The parsed document

    Returns:
        List of dicts with keys: 'text', 'level', 'page'
    """
    toc = []
    for page in doc.pages:
        if page.blocks:
            for block in page.blocks:
                if isinstance(block, TextBlock) and block.category in [
                    'heading',
                    'title',
                    'header',
                ]:
                    toc.append({
                        'text': block.text.strip(),
                        'level': block.level or 1,
                        'page': page.number,
                    })
    return toc


def format_metadata(metadata: Metadata, page_count: int) -> str:
    """
    Format document metadata for display.

    Args:
        metadata: Document metadata object
        page_count: Number of pages in document

    Returns:
        Formatted metadata string
    """

    lines = []

    if metadata is not None and metadata.title:
        lines.append(f'[bold]Title:[/bold] {metadata.title}')
    if metadata is not None and metadata.author:
        lines.append(f'[bold]Author:[/bold] {metadata.author}')
    if metadata is not None and metadata.subject:
        lines.append(f'[bold]Subject:[/bold] {metadata.subject}')
    if metadata is not None and metadata.keywords:
        lines.append(f'[bold]Keywords:[/bold] {metadata.keywords}')
    if metadata is not None and metadata.creator:
        lines.append(f'[bold]Creator:[/bold] {metadata.creator}')
    if metadata is not None and metadata.producer:
        lines.append(f'[bold]Producer:[/bold] {metadata.producer}')
    if metadata is not None and metadata.created_at:
        lines.append(f'[bold]Created:[/bold] {metadata.created_at}')
    if metadata is not None and metadata.updated_at:
        lines.append(f'[bold]Updated:[/bold] {metadata.updated_at}')

    lines.append(f'[bold]Pages:[/bold] {page_count}')

    return '\n'.join(lines) if lines else '[dim]No metadata available[/dim]'


def render_viewer_mode(doc: Document, console: Console):
    """
    Render document in viewer mode with three panels: metadata, TOC, and content.

    Args:
        doc: The parsed document
        console: Console instance for rendering
    """
    # Extract TOC
    toc = extract_toc(doc)

    # Format metadata
    metadata_text = format_metadata(doc.metadata, len(doc.pages))

    # Format TOC
    if toc:
        toc_lines = []
        for item in toc:
            indent = '  ' * (item['level'] - 1)
            toc_lines.append(f"{indent}• {item['text']} [dim](p.{item['page']})[/dim]")
        toc_text = '\n'.join(toc_lines)
    else:
        toc_text = '[dim]No headings found[/dim]'

    # Create markdown content
    markdown_content = doc.markdown()

    # Create layout with three sections
    # Using a Table.grid for the layout since it's more flexible than Layout for this use case
    from rich.columns import Columns

    # Create three panels
    metadata_panel = Panel(
        Text.from_markup(metadata_text),
        padding=(0, 1),
    )

    toc_panel = Panel(
        Text.from_markup(toc_text),
        title='Contents',
        border_style='blue',
        title_align='left',
        padding=(1, 2),
    )

    content_panel = Panel(
        Markdown(markdown_content, code_theme='monokai'),
        title='Document preview in markdown',
        title_align='left',
        padding=(1, 2),
    )

    # Use Layout to create three-column view
    layout = Layout()

    layout.split_column(
        Layout(metadata_panel, name="header", minimum_size=3),
        Layout(name="body", ratio=2)
    )

    layout["body"].split_row(
        Layout(toc_panel, name='toc', ratio=1),
        Layout(content_panel, name='content', ratio=2),
    )

    return layout


def print_result(mode: OutputMode, driver: str, doc: Document, console: Console, preview = None):
    """Print the document content using the requested mode"""
    
    if mode == OutputMode.VIEWER:
        content = render_viewer_mode(doc, console)
    elif mode == OutputMode.JSON:
        content = doc.model_dump_json(indent=2)
    elif mode == OutputMode.PLAIN:
        content = doc.text() if preview is None else doc.text()[:preview]
    
    console.print(content)
    console.newline()

def process_document(file_path: str, driver: str, level: Level) -> Document:
    return Parxy.parse(
        file=file_path,
        level=level.value,
        driver_name=driver,
    )


@app.command()
def parse(
    files: Annotated[
        List[str],
        typer.Argument(
            help='One or more files to parse',
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    driver: Annotated[
        Optional[str],
        typer.Option(
            '--driver',
            '-d',
            help='Driver to use for parsing (default: pymupdf or PARXY_DEFAULT_DRIVER)',
        ),
    ] = None,
    level: Annotated[
        Level,
        typer.Option(
            '--level',
            '-l',
            help='Extraction level',
        ),
    ] = Level.BLOCK,
    mode: Annotated[
        OutputMode,
        typer.Option(
            '--mode',
            '-m',
            help='Output mode: json (JSON serialization), plain (plain text), or viewer (interactive three-panel view)',
        ),
    ] = OutputMode.PLAIN,
    env_file: Annotated[
        str,
        typer.Option(
            '--env',
            '-e',
            help='Path to .env file with configuration',
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = '.env',
    preview: Annotated[
        Optional[int],
        typer.Option(
            '--preview',
            help='Output a preview of the extracted text for each document. Specify the number of characters to preview',
            min=1,
            max=6000,
        ),
    ] = None,
    output_dir: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Directory to save output files. If not specified, output will be printed to console',
            dir_okay=True,
            file_okay=False,
        ),
    ] = None,
):
    """Parse documents."""
    # try:
        # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

        # Special handling for JSON mode with multiple files
        # Generate .jsonl (JSON Lines format) for multiple files
        # if mode == OutputMode.JSON and len(files) > 1 and output_dir:
        #     # Create a single .jsonl file for all documents
        #     jsonl_path = os.path.join(output_dir, 'output.jsonl')

        #     with open(jsonl_path, 'w', encoding='utf-8') as jsonl_file:
        #         for file_path in files:
        #             try:
        #                 with console.shimmer('Processing document...'):
        #                     doc = Parxy.parse(
        #                         file=file_path,
        #                         level=level.value,
        #                         driver_name=driver,
        #                     )

        #                 console.action(file_path)
        #                 console.faint(f'{len(doc.pages)} pages extracted.')

        #                 # Write as single-line JSON to .jsonl file
        #                 json_line = doc.model_dump_json()
        #                 jsonl_file.write(json_line + '\n')

        #             except Exception as e:
        #                 console.error(f'Error processing {file_path}: {str(e)}')
        #                 raise typer.Exit(1)

        #     console.success(f'Saved all documents to: {jsonl_path}')
        #     return

    if len(files) == 1:

        file_path = files[0] 

        with console.shimmer(f'Processing {file_path} using {driver}...'):
            # Parse the document
            doc = process_document(
                file_path=file_path,
                level=level,
                driver=driver,
            )

            # time.sleep(2)

            console.action(file_path)

            print_result(mode=mode, driver=driver, doc=doc, console=console, preview=preview)
        
        return

    console.info('Processing multiple files. Parsing output is saved to file.', panel=True)

    if output_dir is None:
        console.info('Using current working directory to store output files.', panel=True)


    extension = '.md'
    if mode == OutputMode.JSON:
        extension = '.json'
    elif mode == OutputMode.PLAIN:
        extension = '.txt'

    with console.shimmer(f'Processing {len(files)} files using {driver}...'):

        # Process each file
        for file_path in files:
            # try:
                # Parse the document
                doc = process_document(
                    file_path=file_path,
                    level=level,
                    driver=driver,
                )
                base_name = os.path.splitext(os.path.basename(file_path))[0]

                output_path = os.path.join('.' if output_dir == None else output_dir, f'{base_name}{extension}')

                if mode == OutputMode.JSON:
                    content = doc.model_dump_json()
                elif mode == OutputMode.PLAIN:
                    content = doc.text()
                elif mode == OutputMode.VIEWER:
                    content = doc.markdown()

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # time.sleep(1)

                console.action(file_path, space_after=False)
                console.faint(f' ∟ {len(doc.pages)} pages extracted.')
                console.faint(f' ∟ [success]{output_path}[/success]')
                console.newline()

            

            # Save to file or print to console
            # if output_dir:
            #     # Generate output filename

            #     # Save to file
            #     
            #     console.success(f'Saved to: {output_path}')
            # else:
            #     # Print to console
            #     console.print(content)
            #     console.newline()

            # except Exception as e:
            #     console.error(f'Error processing {file_path}: {str(e)}', panel=True)
            #     raise typer.Exit(1)

    # except Exception as e:
    #     console.error(f'Error: {str(e)}')
    #     raise typer.Exit(1)

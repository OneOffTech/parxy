"""Preview command for interactive document viewing."""

from typing import Optional, Annotated, List

import typer
from rich.layout import Layout
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown

from parxy_core.facade import Parxy
from parxy_core.models.models import Document, TextBlock, Metadata

from parxy_cli.models import Level
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
                    toc.append(
                        {
                            'text': block.text.strip(),
                            'level': block.level or 1,
                            'page': page.number,
                        }
                    )
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


def render_viewer_mode(doc: Document) -> Layout:
    """
    Render document in viewer mode with three panels: metadata, TOC, and content.

    Args:
        doc: The parsed document

    Returns:
        Layout object with three-panel view
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
            toc_lines.append(f'{indent}• {item["text"]} [dim](p.{item["page"]})[/dim]')
        toc_text = '\n'.join(toc_lines)
    else:
        toc_text = '[dim]No headings found[/dim]'

    # Create markdown content
    markdown_content = doc.markdown()

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
        Layout(metadata_panel, name='header', minimum_size=3),
        Layout(name='body', ratio=2),
    )

    layout['body'].split_row(
        Layout(toc_panel, name='toc', ratio=1),
        Layout(content_panel, name='content', ratio=2),
    )

    return layout


@app.command()
def preview(
    file: Annotated[
        str,
        typer.Argument(
            help='File to preview',
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
):
    """
    Preview a document in an interactive viewer with metadata, table of contents, and content.

    The preview is displayed in a scrollable three-panel layout showing:
    - Document metadata (title, author, pages, etc.)
    - Table of contents extracted from headings
    - Document content rendered as markdown
    """

    with console.shimmer(f'Processing {file} using {driver}...'):
        # Parse the document
        doc = Parxy.parse(
            file=file,
            level=level.value,
            driver_name=driver,
        )

    # Render the viewer layout
    layout = render_viewer_mode(doc)

    # Use Rich's pager for scrollable output with styles preserved
    console.print(layout)
    # with console.pager(styles=True):

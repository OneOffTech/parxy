"""Command line interface for Parxy document processing."""

import os
import sys
from typing import Optional, List


import typer
from rich.console import Console

from parxy_core.facade import Parxy

from parxy_cli.models import Level

app = typer.Typer()

console = Console()


@app.command()
def parse(
    files: List[str] = typer.Argument(
        ...,
        help='One or more files to parse',
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    driver: Optional[str] = typer.Option(
        None,
        '--driver',
        '-d',
        help='Driver to use for parsing (default: pymupdf or PARXY_DEFAULT_DRIVER)',
    ),
    level: Level = typer.Option(
        Level.BLOCK,
        '--level',
        '-l',
        help='Extraction level',
    ),
    env_file: Optional[str] = typer.Option(
        '.env',
        '--env',
        '-e',
        help='Path to .env file with configuration',
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    preview: Optional[int] = typer.Option(
        None,
        '--preview',
        help='Output a preview of the extracted text for each document. Specify the number of characters to preview',
        min=1,
        max=6000,
    ),
    output_dir: Optional[str] = typer.Option(
        None,
        '--output',
        '-o',
        help='Directory to save output files. If not specified, output will be printed to console',
        dir_okay=True,
        file_okay=False,
    ),
):
    """Parse documents."""
    try:
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        console.print('Processing documents...')

        # Process each file
        for file_path in files:
            try:
                console.print('----')

                # Parse the document
                doc = Parxy.parse(
                    file=file_path,
                    level=level.value,
                    driver_name=driver,
                )

                console.print(f'[bold blue]{file_path} (pages={len(doc.pages)})[/]')

                text_content = doc.text() if preview is None else doc.text()[:preview]

                if output_dir:
                    # Generate output filename
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    output_path = os.path.join(output_dir, f'{base_name}.txt')

                    # Save to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    console.print(f'[green]Saved to: {output_path}[/]\n')
                else:
                    # Print to console
                    console.print('\n' + text_content + '\n')

            except Exception as e:
                console.print(f'[bold red]Error processing {file_path}:[/] {str(e)}')
                console.print_exception(e)

    except Exception as e:
        console.print(f'[bold red]Error:[/] {str(e)}')
        console.print_exception(e)
        raise typer.Exit()

"""Command line interface for Parxy document processing."""

import os
import sys
from typing import Optional, List, Annotated


import typer

from parxy_core.facade import Parxy

from parxy_cli.models import Level
from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


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
    try:
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Process each file
        for file_path in files:
            try:
                with console.shimmer('Processing document...'):
                    # Parse the document
                    doc = Parxy.parse(
                        file=file_path,
                        level=level.value,
                        driver_name=driver,
                    )

                console.action(file_path)
                console.faint(f'{len(doc.pages)} pages extracted.')

                text_content = doc.text() if preview is None else doc.text()[:preview]

                if output_dir:
                    # Generate output filename
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    output_path = os.path.join(output_dir, f'{base_name}.txt')

                    # Save to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    console.success(f'Saved to: {output_path}')
                else:
                    # Print to console
                    console.print(text_content)
                    console.newline()

            except Exception as e:
                console.error(f'Error processing {file_path}: {str(e)}')

    except Exception as e:
        console.error(f'Error: {str(e)}')
        raise typer.Exit()

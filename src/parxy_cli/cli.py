"""Command line interface for Parxy document processing."""

import os
import sys
from typing import Optional, List
from enum import Enum

import typer
from rich import print
from rich.console import Console

from parxy_core.facade import Parxy


# Create typer app
app = typer.Typer(
    name='parxy',
    help='Parxy document processing gateway on the command line.',
    add_completion=False,
)

# Create rich console
console = Console()


class Level(str, Enum):
    """Valid extraction levels."""

    PAGE = 'page'
    BLOCK = 'block'
    LINE = 'line'
    SPAN = 'span'
    CHARACTER = 'character'


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
    """Parse documents using Parxy."""
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
        sys.exit(1)


@app.command()
def markdown(
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
    output_dir: Optional[str] = typer.Option(
        None,
        '--output',
        '-o',
        help='Directory to save markdown files. If not specified, output will be printed to console',
        dir_okay=True,
        file_okay=False,
    ),
    combine: bool = typer.Option(
        False,
        '--combine',
        '-c',
        help='Combine all documents into a single markdown file',
    ),
):
    """Parse documents and return Markdown output, if multiple documents are provided they will be separated."""
    try:
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        console.print('Processing documents...')

        # For combined output
        combined_content = []

        # Process each file
        for file_path in files:
            try:
                # Parse the document
                doc = Parxy.parse(
                    file=file_path,
                    level=level.value,
                    driver_name=driver,
                )

                # Prepare markdown content
                file_info = f"""```yaml
file: "{file_path}"
pages: {len(doc.pages)}
```"""
                header = f'# {os.path.basename(file_path)}\n'
                content = doc.markdown()

                markdown_content = f'{file_info}\n{header}\n{content}'

                if output_dir and not combine:
                    # Generate output filename
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    output_path = os.path.join(output_dir, f'{base_name}.md')

                    # Save to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    console.print(f'[green]Saved to: {output_path}[/]')

                elif not output_dir:
                    # Print to console
                    console.print(markdown_content)
                    console.print('\n\n---\n\n')

                if combine:
                    combined_content.append(markdown_content)

            except Exception as e:
                console.print(f'[bold red]Error processing {file_path}:[/] {str(e)}')

        # Save combined content if requested
        if combine and output_dir and combined_content:
            output_path = os.path.join(output_dir, 'combined_output.md')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n\n---\n\n'.join(combined_content))
            console.print(f'[green]Combined output saved to: {output_path}[/]')

    except Exception as e:
        console.print(f'[bold red]Error:[/] {str(e)}')
        console.print_exception(e)
        sys.exit(1)


@app.command()
def drivers():
    """List supported drivers."""

    drivers = Parxy.drivers()

    for driver_name in drivers:
        print(driver_name)


@app.command()
def env():
    """Create an environment file with Parxy configuration."""
    from importlib.resources import files

    # Get the example file content from the package
    try:
        example_content = files('parxy_cli').joinpath('.env.example').read_text()

        # Check if .env already exists
        if os.path.exists('.env'):
            console.print('[bold yellow]Warning: .env file already exists[/]')
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.print('Aborted.')
                return

        # Write the content to .env
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(example_content)

        console.print('[green]Created .env file with default configuration[/]')
        console.print('Edit the file to configure your settings')
    except Exception as e:
        console.print(f'[bold red]Error creating .env file:[/] {str(e)}')
        sys.exit(1)


@app.command()
def docker():
    """Create a Docker Compose configuration file to run self-hosted document processing services (experimental)."""

    from importlib.resources import files

    # Get the example file content from the package
    try:
        example_content = (
            files('parxy_cli').joinpath('compose.example.yaml').read_text()
        )

        # Check if compose.yaml already exists
        if os.path.exists('compose.yaml'):
            console.print('[bold yellow]Warning: compose.yaml file already exists[/]')
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.print('Aborted.')
                return

        # Write the content to compose.yaml
        with open('compose.yaml', 'w', encoding='utf-8') as f:
            f.write(example_content)

        console.print('[green]Created compose.yaml file with default configuration[/]')
        console.print(
            'Execute `docker compose pull` and `docker compose up -d` to start the services.'
        )
    except Exception as e:
        console.print(f'[bold red]Error creating compose.yaml file:[/] {str(e)}')
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    app()

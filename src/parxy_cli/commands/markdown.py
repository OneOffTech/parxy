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
    """Parse documents to Markdown."""
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
        raise typer.Exit()

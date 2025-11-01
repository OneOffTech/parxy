import os
from typing import Optional, List, Annotated

import typer

from parxy_core.facade import Parxy
from parxy_cli.models import Level
from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


@app.command()
def markdown(
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
    output_dir: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Directory to save markdown files. If not specified, output will be printed to console',
            dir_okay=True,
            file_okay=False,
        ),
    ] = None,
    combine: Annotated[
        bool,
        typer.Option(
            '--combine',
            '-c',
            help='Combine all documents into a single markdown file',
        ),
    ] = False,
):
    """Parse documents to Markdown."""
    try:
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # For combined output
        combined_content = []

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
                    console.success(f'Saved to: {output_path}')

                elif not output_dir:
                    # Print to console
                    console.print(markdown_content)
                    console.rule()
                    console.newline()

                if combine:
                    combined_content.append(markdown_content)

            except Exception as e:
                console.error(f'Error processing {file_path}: {str(e)}')

        # Save combined content if requested
        if combine and output_dir and combined_content:
            output_path = os.path.join(output_dir, 'combined_output.md')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n\n---\n\n'.join(combined_content))
            console.success(f'Combined output saved to: {output_path}')

    except Exception as e:
        console.error(f'Error: {str(e)}')
        raise typer.Exit()

"""Command line interface for Parxy document processing."""

import os
import sys

import typer
from rich.console import Console

app = typer.Typer()

console = Console()


@app.command()
def docker():
    """Create a Docker Compose file to run self-hostable parsers (experimental)."""

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

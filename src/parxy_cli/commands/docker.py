from pathlib import Path

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

        compose_file_path: Path = Path.cwd() / 'compose.yaml'

        # Check if compose.yaml already exists
        if compose_file_path.exists():
            console.print('[bold yellow]Warning: compose.yaml file already exists[/]')
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.print('Aborted.')
                raise typer.Exit()

        # Write the content to compose.yaml
        compose_file_path.write_text(example_content)

        console.print('[green]Created compose.yaml file with default configuration[/]')
        console.print(
            'Execute `docker compose pull` and `docker compose up -d` to start the services.'
        )
    except Exception as e:
        console.print(f'[bold red]Error creating compose.yaml file:[/] {str(e)}')
        raise typer.Exit(1)

from pathlib import Path

import typer

from parxy_cli.console.console import Console

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
            console.warning('compose.yaml file already exists')
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.muted('Aborted.')
                raise typer.Exit()

        # Write the content to compose.yaml
        compose_file_path.write_text(example_content)

        console.success('Created compose.yaml file with default configuration')
        console.muted(
            'Execute `docker compose pull` and `docker compose up -d` to start the services.'
        )
    except Exception as e:
        console.error(f'Error creating compose.yaml file: {str(e)}')
        raise typer.Exit(1)

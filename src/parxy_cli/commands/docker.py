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
        example_compose_content = (
            files('parxy_cli').joinpath('compose.example.yaml').read_text()
        )
        example_otel_content = (
            files('parxy_cli')
            .joinpath('otel-collector-config.example.yaml')
            .read_text()
        )

        console.action('Create compose.yaml file')

        compose_file_path: Path = Path.cwd() / 'compose.yaml'

        otel_file_path: Path = Path.cwd() / 'otel-collector-config.yaml'

        # Check if compose.yaml already exists
        if compose_file_path.exists():
            console.highlight('compose.yaml file already exists')
            console.newline()
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.faint('Leaving compose.yaml as is.')
                return

        # Write the content to compose.yaml
        compose_file_path.write_text(example_compose_content)

        if otel_file_path.exists():
            console.highlight('otel-collector-config.yaml file already exists')
            console.newline()
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.faint('Leaving otel-collector-config.yaml as is.')
                return

        # Write the content to compose.yaml
        otel_file_path.write_text(example_otel_content)

        console.print(
            '[success]Created compose.yaml[/success] file with default configuration.'
        )
        console.newline()
        console.markdown(
            'Execute `docker compose pull` and `docker compose up -d` to start the services.'
        )

    except Exception as e:
        console.error(f'Error creating compose.yaml file: {str(e)}')
        raise typer.Exit(1)

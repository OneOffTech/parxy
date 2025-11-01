import typer
from pathlib import Path

from parxy_cli.console.console import Console


app = typer.Typer()

console = Console()


@app.command()
def env():
    """Create an environment file with Parxy configuration."""
    from importlib.resources import files

    try:
        # Get the example file content from the package
        example_content = files('parxy_cli').joinpath('.env.example').read_text()

        env_file_path: Path = Path.cwd() / '.env'

        # Check if .env already exists
        if env_file_path.exists():
            console.warning('.env file already exists')
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.muted('Aborted.')
                raise typer.Exit()

        # Write the content to .env
        env_file_path.write_text(example_content)

        console.success('Created .env file with default configuration')
        console.muted('Edit the file to configure your settings')
    except Exception as e:
        console.error(f'Error creating .env file: {str(e)}')
        raise typer.Exit(1)

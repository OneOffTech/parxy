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

        console.action('Create env file')

        # Check if .env already exists
        if env_file_path.exists():
            console.highlight('.env file already exists')
            console.newline()
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.faint('Leaving your file as is.')
                return

        # Write the content to .env
        env_file_path.write_text(example_content)

        console.success(
            '[success]Created .env file[/success] with default configuration.'
        )
        console.faint('Edit the file to configure your settings.')
    except Exception as e:
        console.error(f'Error creating .env file: {str(e)}')
        raise typer.Exit(1)

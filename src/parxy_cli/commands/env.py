import typer
from rich.console import Console
from pathlib import Path


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
            console.print('[bold yellow]Warning: .env file already exists[/]')
            overwrite = typer.confirm('Do you want to overwrite it?', default=False)
            if not overwrite:
                console.print('Aborted.')
                raise typer.Exit()

        # Write the content to .env
        env_file_path.write_text(example_content)

        console.print('[green]Created .env file with default configuration[/]')
        console.print('Edit the file to configure your settings')
    except Exception as e:
        console.print(f'[bold red]Error creating .env file:[/] {str(e)}')
        raise typer.Exit(1)

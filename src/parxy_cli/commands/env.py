import os
import sys

import typer
from rich.console import Console


app = typer.Typer()

console = Console()


@app.command()
def env():
    """Create an environment file with Parxy configuration."""
    from importlib.resources import files

    # Get the example file content from the package
    try:
        example_content = files('parxy_cli').joinpath('.env.example').read_text()

        print(os.path.abspath('.'))

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

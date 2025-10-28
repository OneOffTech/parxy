"""Command line interface for Parxy document processing."""

import typer
from rich import print
from rich.console import Console

app = typer.Typer()

console = Console()

app = typer.Typer()

console = Console()


@app.command()
def version():
    """Print Parxy version information"""

    print('VERSION')

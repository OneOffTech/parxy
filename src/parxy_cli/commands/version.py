"""Command line interface for Parxy document processing."""

import sys
import platform
from importlib.metadata import version as metadata_version
import typer

from parxy_cli.console.console import Console


app = typer.Typer()

console = Console()


@app.command()
def version():
    """Print Parxy version information."""
    try:
        parxy_version = metadata_version('parxy')
    except Exception:
        parxy_version = 'Development version'

    console.highlight('Parxy. Every document matters.')
    console.newline()

    console.info(f'Version: {parxy_version}')
    console.muted(
        f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'
    )
    console.muted(f'Platform: {platform.platform()}')

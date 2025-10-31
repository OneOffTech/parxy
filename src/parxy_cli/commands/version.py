"""Command line interface for Parxy document processing."""

import sys
import platform
from importlib.metadata import version as metadata_version
import typer
from rich import print


app = typer.Typer()


@app.command()
def version():
    """Print Parxy version information."""
    try:
        parxy_version = metadata_version('parxy')
    except Exception:
        parxy_version = 'Development version'

    print('Parxy. Every document matters.\n')

    print(f'Version: {parxy_version}')

    print(
        f'Python Version {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'
    )
    print(f'Platform {platform.platform()}')

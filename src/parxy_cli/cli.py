"""Command line interface for Parxy."""

import os
import sys
from typing import Optional, List

import typer
from typing_extensions import Annotated
from importlib.metadata import version as metadata_version

from parxy_cli.console.console import Console
from parxy_cli.commands.docker import app as docker_command
from parxy_cli.commands.parse import app as parse_command
from parxy_cli.commands.drivers import app as drivers_command
from parxy_cli.commands.env import app as env_command
from parxy_cli.commands.version import app as version_command
from parxy_cli.commands.markdown import app as markdown_command


# Create typer app
app = typer.Typer(
    name='parxy',
    help='Parxy document processing gateway.',
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)

# Create Flexoki-themed console
console = Console()


def version_callback(value: bool):
    if value:
        try:
            parxy_version = metadata_version('parxy')
        except Exception:
            parxy_version = 'Development version'

        console.print(f'[{console.COLORS["blue"]}]▣ Parxy[/{console.COLORS["blue"]}]. Every document matters.')
        console.newline()
        console.info(f'Version: {parxy_version}')
        console.newline()
        console.muted('For more information on Parxy run `parxy version`.')
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            '--version',
            callback=version_callback,
            is_eager=True,
            help='Show Parxy version',
        ),
    ] = None,
):
    """Define the common command options"""

    console.print(f'[{console.COLORS["blue"]}]📄 Parxy[/{console.COLORS["blue"]}]')


app.add_typer(docker_command)
app.add_typer(parse_command)
app.add_typer(drivers_command)
app.add_typer(env_command)
app.add_typer(version_command)
app.add_typer(markdown_command)


def main():
    """Entry point for the CLI."""
    app()

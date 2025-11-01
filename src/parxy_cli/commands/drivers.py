import typer

from parxy_core.facade import Parxy
from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


@app.command()
def drivers():
    """List supported drivers."""

    drivers = Parxy.drivers()

    console.info('Available drivers:')
    console.newline()

    for driver_name in drivers:
        console.print(f'  • {driver_name}', style='muted')

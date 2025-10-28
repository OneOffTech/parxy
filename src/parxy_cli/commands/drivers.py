import typer
from rich import print
from rich.console import Console

from parxy_core.facade import Parxy

app = typer.Typer()

console = Console()


@app.command()
def drivers():
    """List supported drivers."""

    drivers = Parxy.drivers()

    for driver_name in drivers:
        print(driver_name)

import typer

from parxy_core.facade import Parxy
from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


@app.command()
def drivers():
    """List supported drivers."""

    drivers = Parxy.drivers()

    console.action('Parxy available drivers')

    console.print(f'{len(drivers)} drivers supported:')

    driver_list = '\n'.join(f'- {driver}' for driver in drivers)
    console.markdown(driver_list)

import typer

from rich.table import Table
from pydantic import ValidationError

from parxy_core.facade import Parxy
from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


@app.command()
def drivers():
    """List supported drivers."""

    factory = Parxy._get_factory()

    # Get supported and custom drivers
    supported_drivers = factory.get_supported_drivers()
    custom_drivers = factory.get_custom_drivers()

    drivers = supported_drivers + custom_drivers

    console.action('Parxy drivers', space_after=False)

    console.print(
        f'[faint]⎿ [/faint] [bold]{len(drivers)}[/bold] driver{"s" if len(drivers) > 1 else ""} supported ({len(custom_drivers)} custom{"s" if len(custom_drivers) > 1 else ""}).'
    )

    if not drivers:
        return

    console.newline()

    with console.shimmer(f'Checking installed drivers...'):
        # Create a table for displaying driver information
        table = Table(
            show_header=True,
            # header_style='bold',
            show_lines=False,
            padding=(0, 1),
        )

        table.add_column('Driver', no_wrap=True)
        table.add_column('Status', no_wrap=True)
        table.add_column('Type', style='faint')
        table.add_column('Details', style='faint')

        # Check each driver
        for driver_name in drivers:
            driver_type = 'custom' if driver_name in custom_drivers else 'built-in'

            try:
                # Attempt to create driver instance
                factory.driver(driver_name)
                status = '[green]✓ Ready[/green]'
                details = ''
            except ImportError as e:
                status = '[red]✗ Not installed[/red]'
                # Extract the missing module name from the error
                missing_module = (
                    str(e).split("'")[1] if "'" in str(e) else 'dependencies'
                )
                details = f'Missing: {missing_module}'
            except Exception as e:
                status = '[yellow]⚠ Installed with warnings[/yellow]'
                details = str(e)[:50].strip()

            table.add_row(driver_name, status, driver_type, details)

        console.print(table)
        console.newline()

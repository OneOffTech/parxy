"""Command to launch the Parxy TUI."""

from pathlib import Path
from typing import Annotated

import typer

from parxy_cli.console.console import Console

app = typer.Typer(
    name='tui', help='Launch the Parxy TUI for interactive parser comparison'
)

console = Console()


@app.callback(invoke_without_command=True)
def tui(
    workspace: Annotated[
        str,
        typer.Argument(
            help='Path to the workspace folder containing documents to process',
        ),
    ],
):
    """
    Launch the Parxy TUI for interactive parser comparison.

    The TUI provides an interactive interface to:
    - Browse files in your workspace
    - Select multiple parsers to compare
    - View parsing results side-by-side
    - See JSON and Markdown diffs between parsers

    Requires the tui extra: pip install 'parxy[tui]'

    Examples:

        # Launch TUI with current directory
        parxy tui .

        # Launch TUI with specific folder
        parxy tui /path/to/documents
    """
    workspace_path = Path(workspace).resolve()

    if not workspace_path.exists():
        console.error(f'Workspace path does not exist: {workspace_path}')
        raise typer.Exit(1)

    if not workspace_path.is_dir():
        console.error(f'Workspace path is not a directory: {workspace_path}')
        raise typer.Exit(1)

    try:
        from parxy_cli.tui.app import run_tui
    except ImportError:
        console.error(
            "The TUI requires the 'tui' extra. Install it with:\n\n"
            "    pip install 'parxy[tui]'"
        )
        raise typer.Exit(1)

    console.info(f'Starting Parxy TUI with workspace: {workspace_path}')

    try:
        run_tui(workspace_path)
    except Exception as e:
        console.error(f'Error running TUI: {str(e)}')
        raise typer.Exit(1)

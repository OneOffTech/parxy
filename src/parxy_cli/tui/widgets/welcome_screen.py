"""Welcome screen widget for the main area."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Center
from textual.widgets import Button, Label, Static


class WelcomeScreen(Container):
    """Welcome screen displayed before parsing begins."""

    DEFAULT_CSS = """
    WelcomeScreen {
        width: 30;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the welcome screen."""
        with Vertical(id='welcome-container'):
            yield Static('')  # Spacer
            with Center():
                yield Label('[bold]Welcome to Parxy TUI[/bold]', id='welcome-title')
            with Center():
                yield Static(
                    'Select one or more files from the sidebar and choose parsers to compare',
                    id='welcome-message',
                )
            yield Static('')  # Spacer
            with Center():
                yield Button('Start Parsing', id='parse-button', variant='primary')
            yield Static('')  # Spacer

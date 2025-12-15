"""Welcome container combining logo, welcome screen and parser selector."""

from textual.app import ComposeResult
from textual.containers import Vertical

from parxy_cli.tui.widgets.logo import Logo
from parxy_cli.tui.widgets.welcome_screen import WelcomeScreen
from parxy_cli.tui.widgets.parser_selector import ParserSelector


class WelcomeContainer(Vertical):
    """Container that combines logo, welcome message, and parser selector."""

    def compose(self) -> ComposeResult:
        """Compose the welcome container."""
        yield Logo(classes='mb-1', id='logo')
        yield ParserSelector(id='parser-selector')

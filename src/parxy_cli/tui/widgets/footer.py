"""Footer widget — status bar + hints."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class Footer(Horizontal):
    """Status + hints footer docked to the bottom of each screen."""

    def compose(self) -> ComposeResult:
        yield Static('Ready', id='status-bar')
        yield Static('', id='footer-hints')

    def set_hints(self, text: str) -> None:
        """Update the right-hand hints text."""
        self.query_one('#footer-hints', Static).update(text)

"""Parser selector widget for choosing parsers to run."""

from typing import List

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Label, Static
from textual.message import Message

from parxy_core.facade import Parxy


class Footer(Horizontal):
    """Widget for selecting parsers."""

    def compose(self) -> ComposeResult:
        """Compose the parser selector."""
        yield Static('Ready', id='status-bar')
        yield Static(
            '[$foreground]ctrl+p[/$foreground] commands', classes='command-palette'
        )

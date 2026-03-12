"""Parxy header widget — consistent top chrome across all screens."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Button


class _LogoLabel(Static):
    """Clickable logo/breadcrumb label on the left of the header."""

    def on_click(self) -> None:
        if len(self.app.screen_stack) > 2:
            self.app.pop_screen()


class _PaletteLabel(Static):
    """Clickable command-palette label on the right of the header."""

    def on_click(self) -> None:
        self.app.action_command_palette()


class ParxyHeader(Horizontal):
    """1-line header docked to the top; shows breadcrumb + palette shortcut."""

    DEFAULT_CSS = """
    ParxyHeader {
        dock: top;
        height: 1;
        layout: horizontal;
    }

    #header-logo {
        width: 1fr;
        height: 1;
        content-align: left middle;
        color: $primary;
        padding: 0 1;
    }

    #header-commands {
        width: auto;
        height: 1;
        content-align: right middle;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, breadcrumb: str = '', *args, **kwargs):
        self._breadcrumb = breadcrumb
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        logo_text = '▣ parxy'
        if self._breadcrumb:
            logo_text += f' / {self._breadcrumb}'
        yield _LogoLabel(logo_text, id='header-logo')
        yield _PaletteLabel('ctrl+p commands', id='header-commands')

    def update_breadcrumb(self, text: str) -> None:
        """Update the breadcrumb portion of the logo label."""
        self._breadcrumb = text
        new_text = '▣ parxy'
        if text:
            new_text += f' / {text}'
        self.query_one('#header-logo', _LogoLabel).update(new_text)

"""Main TUI application for Parxy parser comparison."""

from pathlib import Path
from typing import Optional

from textual.app import App
from textual.binding import Binding

from parxy_cli.tui.screens.browse import BrowseScreen
from parxy_cli.tui.screens.folder_selection import FolderSelectionScreen
from parxy_cli.tui.screens.viewer import ViewerScreen


class ParxyTUI(App):
    """Parxy TUI — interactive document parser comparison."""

    CSS_PATH = 'app.tcss'

    BINDINGS = [
        Binding('ctrl+q', 'quit', 'Quit', key_display='Ctrl+Q'),
    ]

    def __init__(self, workspace: Optional[Path] = None):
        super().__init__()
        self._initial_workspace = workspace
        self.theme = 'flexoki'

    def on_mount(self) -> None:
        if self._initial_workspace is not None:
            self.push_screen(BrowseScreen(self._initial_workspace))
        else:
            self.push_screen(FolderSelectionScreen())

    # ------------------------------------------------------------------
    # Navigation helpers called by screens
    # ------------------------------------------------------------------

    def open_workspace(self, path: Path) -> None:
        """Push the browse screen for the given workspace folder."""
        self.push_screen(BrowseScreen(path))

    def open_file(self, file_path: Path, workspace: Path) -> None:
        """Push the viewer screen for the given file."""
        self.push_screen(ViewerScreen(file_path, workspace))


def run_tui(workspace: Optional[Path] = None) -> None:
    """Run the TUI application."""
    ParxyTUI(workspace).run()

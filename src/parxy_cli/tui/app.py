"""Main TUI application for Parxy parser comparison."""

from pathlib import Path
from typing import Optional

from textual.app import App
from textual.binding import Binding
from textual.widgets import Static

from parxy_cli.tui.screens.browse import BrowseScreen
from parxy_cli.tui.screens.folder_selection import FolderSelectionScreen
from parxy_cli.tui.screens.viewer import ViewerScreen
from parxy_cli.tui.widgets.history import HistoryModal, save_to_history


class ParxyTUI(App):
    """Parxy TUI — interactive document parser comparison."""

    CSS_PATH = 'app.tcss'

    BINDINGS = [
        Binding('ctrl+q', 'quit', 'Quit', key_display='Ctrl+Q'),
        Binding('ctrl+h', 'show_history', 'History', key_display='Ctrl+H'),
        Binding('ctrl+c', 'try_quit', show=False, priority=True),
    ]

    def __init__(self, workspace: Optional[Path] = None):
        super().__init__()
        self._initial_workspace = workspace
        self._quit_pending = False
        self.theme = 'flexoki'

    def on_mount(self) -> None:
        if self._initial_workspace is not None:
            self.open_workspace(self._initial_workspace)
        else:
            self.push_screen(FolderSelectionScreen())

    # ------------------------------------------------------------------
    # Navigation helpers called by screens
    # ------------------------------------------------------------------

    def open_workspace(self, path: Path) -> None:
        """Push the browse screen for the given workspace folder."""
        save_to_history(path)
        self.push_screen(BrowseScreen(path))

    def open_file(self, file_path: Path, workspace: Path) -> None:
        """Push the viewer screen for the given file."""
        self.push_screen(ViewerScreen(file_path, workspace))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_try_quit(self) -> None:
        if self._quit_pending:
            self.exit()
        else:
            self._quit_pending = True
            try:
                self.query_one('#status-bar', Static).update(
                    'Press Ctrl+C again to quit'
                )
            except Exception:
                pass
            self.set_timer(2.0, self._reset_quit_pending)

    def _reset_quit_pending(self) -> None:
        self._quit_pending = False

    def action_show_history(self) -> None:
        def _on_close(result: Optional[Path]) -> None:
            if result is not None:
                self.open_workspace(result)

        self.push_screen(HistoryModal(), _on_close)


def run_tui(workspace: Optional[Path] = None) -> None:
    """Run the TUI application."""
    ParxyTUI(workspace).run()

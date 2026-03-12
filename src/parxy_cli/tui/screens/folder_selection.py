"""Folder selection screen - entry point of the TUI."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DirectoryTree, Input, Label, Static
from textual.containers import Vertical

from parxy_cli.tui.widgets.logo import Logo
from parxy_cli.tui.widgets.footer import Footer
from parxy_cli.tui.widgets.header import ParxyHeader


class FolderOnlyTree(DirectoryTree):
    """DirectoryTree that shows only directories."""

    def filter_paths(self, paths):
        return [p for p in paths if p.is_dir()]


class FolderSelectionScreen(Screen):
    """Screen for selecting the workspace folder."""

    DEFAULT_CSS = """
    FolderSelectionScreen {
        layout: vertical;
    }

    #folder-selection-body {
        height: 1fr;
        layout: vertical;
        padding: 1 2;
    }

    #folder-selection-title {
        padding: 1 0;
        color: $text-muted;
    }

    #folder-path-input {
        margin: 1 0;
    }

    #folder-tree {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding('ctrl+p', 'command_palette', 'Commands', show=False),
    ]

    def __init__(self, start_path: Path = Path.home(), *args, **kwargs):
        self.start_path = start_path
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield ParxyHeader()
        with Vertical(id='folder-selection-body'):
            yield Logo()
            yield Label('Select a workspace folder', id='folder-selection-title')
            yield Input(
                placeholder='Type a folder path and press Enter...',
                id='folder-path-input',
            )
            yield FolderOnlyTree(str(self.start_path), id='folder-tree')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#folder-path-input', Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != 'folder-path-input':
            return
        path = Path(event.value.strip()).expanduser().resolve()
        if path.is_dir():
            self.app.open_workspace(path)  # type: ignore[attr-defined]
        else:
            self.query_one('#status-bar', Static).update(
                f'Path not found: {event.value}'
            )

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self.app.open_workspace(event.path)  # type: ignore[attr-defined]

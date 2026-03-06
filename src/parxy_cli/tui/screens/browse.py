"""Browse screen - folder navigation and file list."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DirectoryTree, Input, Label, Static

from parxy_cli.tui.widgets.file_list import FileList
from parxy_cli.tui.widgets.file_tree_selector import FilteredDirectoryTree
from parxy_cli.tui.widgets.footer import Footer


class FolderNavTree(FilteredDirectoryTree):
    """Folder navigation tree — shows only directories, supports search."""

    def filter_paths(self, paths):
        # Apply search-query filtering from the parent class, then restrict to dirs.
        filtered = super().filter_paths(paths)
        return [p for p in filtered if p.is_dir()]


class BrowseScreen(Screen):
    """Screen for browsing files in a workspace folder."""

    DEFAULT_CSS = """
    BrowseScreen {
        layout: vertical;
    }

    #browse-content {
        height: 1fr;
    }

    #browse-nav-panel {
        width: 1fr;
        height: 100%;
        layout: vertical;
        padding: 1;
        background: $surface;
    }

    BrowseScreen.nav-hidden #browse-nav-panel {
        display: none;
    }

    #browse-file-panel {
        width: 2fr;
        height: 100%;
    }

    #browse-nav-search {
        margin-bottom: 1;
    }

    #browse-nav-tree {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding('ctrl+e', 'pop_screen', 'Folder selection', key_display='Ctrl+E'),
        Binding('ctrl+k', 'open_viewer', 'View file', key_display='Ctrl+K'),
        Binding('ctrl+i', 'toggle_nav', 'Toggle folders', key_display='Ctrl+I'),
        Binding('ctrl+p', 'command_palette', 'Commands', show=False),
    ]

    def __init__(self, workspace: Path, *args, **kwargs):
        self.workspace = workspace
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal(id='browse-content'):
            with Vertical(id='browse-nav-panel'):
                yield Label(self.workspace.name, classes='section-title')
                yield Input(
                    placeholder='Search folders...',
                    id='browse-nav-search',
                    compact=True,
                )
                yield FolderNavTree(str(self.workspace), id='browse-nav-tree')
            with Vertical(id='browse-file-panel'):
                yield FileList(self.workspace, id='file-list')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#status-bar', Static).update(
            f'Browsing {self.workspace.name}/ — Ctrl+K to open file, Ctrl+I to toggle folders'
        )

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Update the file list when the user navigates to a sub-folder."""
        self.query_one('#file-list', FileList).refresh_files(event.path)
        self.query_one('#status-bar', Static).update(f'Browsing {event.path.name}/')

    def on_file_list_file_selected(self, event: FileList.FileSelected) -> None:
        """Open the viewer for the activated file."""
        self.app.open_file(event.path, self.workspace)  # type: ignore[attr-defined]

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'browse-nav-search':
            self.query_one('#browse-nav-tree', FolderNavTree).set_search_query(
                event.value
            )

    def action_open_viewer(self) -> None:
        file_list = self.query_one('#file-list', FileList)
        if file_list.focused_file:
            self.app.open_file(file_list.focused_file, self.workspace)  # type: ignore[attr-defined]
        else:
            self.query_one('#status-bar', Static).update(
                'No file selected — use arrow keys to highlight a file first'
            )

    def action_toggle_nav(self) -> None:
        self.toggle_class('nav-hidden')
        visible = 'nav-hidden' not in self.classes
        self.query_one('#status-bar', Static).update(
            'Folders panel shown' if visible else 'Folders panel hidden'
        )

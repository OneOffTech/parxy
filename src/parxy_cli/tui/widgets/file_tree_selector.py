"""File tree selector widget with search functionality."""

from pathlib import Path
from typing import Set

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import DirectoryTree, Input, Label
from textual.message import Message


class FilteredDirectoryTree(DirectoryTree):
    """Directory tree that filters for document files."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc', '.html', '.htm', '.xml'}

    def __init__(self, path: str, *args, **kwargs):
        self._search_query: str = ""
        super().__init__(path, *args, **kwargs)

    def filter_paths(self, paths):
        """Filter to show only directories and supported document files."""
        filtered = [
            path for path in paths
            if path.is_dir() or path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]
        
        # Apply search filter if query exists
        if self._search_query:
            query_lower = self._search_query.lower()
            filtered = [
                path for path in filtered
                if path.is_dir() or query_lower in path.name.lower()
            ]
        
        return filtered

    def set_search_query(self, query: str) -> None:
        """Set the search query and reload the tree."""
        self._search_query = query
        self.reload()


class FileTreeSelector(Container):
    """A widget that combines a file tree with a search box."""

    class FileSelected(Message):
        """Message sent when a file is selected from the tree."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def __init__(self, workspace: Path, *args, **kwargs):
        self.workspace = workspace
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the file tree selector."""
        with Vertical(id="file-tree-selector-container"):
            yield Label("Files", classes="section-title")
            yield Input(
                placeholder="Search files...",
                id="file-search-input",
                compact=True
            )
            yield FilteredDirectoryTree(
                str(self.workspace),
                id="file-tree"
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "file-search-input":
            tree = self.query_one("#file-tree", FilteredDirectoryTree)
            tree.set_search_query(event.value)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection and bubble up a custom message."""
        # Post a custom message that can be caught by parent containers
        self.post_message(self.FileSelected(event.path))

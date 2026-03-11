"""File list widget showing PDFs with processing status."""

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable, Input, Label

from parxy_cli.tui.widgets.workspace_viewer import find_processed_files


class FileList(Vertical):
    """Shows PDF files in a directory with their processing status."""

    BINDINGS = [
        Binding('space', 'open_focused', 'Open file', show=False),
    ]

    class FileSelected(Message):
        """Emitted when the user activates a file row (Enter or double-click)."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    DEFAULT_CSS = """
    FileList {
        height: 100%;
        layout: vertical;
        padding: 1;
    }

    #file-list-search {
        margin-bottom: 1;
    }

    #file-list-table {
        height: 1fr;
    }
    """

    def __init__(self, workspace: Path, *args, **kwargs):
        self._workspace = workspace
        self._search: str = ''
        self._all_pdfs: list[Path] = []
        self.focused_file: Optional[Path] = None
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Label('Files', classes='section-title')
        yield Input(
            placeholder='Search files...',
            id='file-list-search',
            compact=True,
        )
        yield DataTable(id='file-list-table', cursor_type='row')

    def on_mount(self) -> None:
        self._build_table()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh_files(self, workspace: Path) -> None:
        """Switch to a new directory and rebuild the table."""
        self._workspace = workspace
        self.focused_file = None
        self._build_table()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_table(self) -> None:
        table = self.query_one('#file-list-table', DataTable)
        table.clear(columns=True)
        table.add_column('File', key='file')
        table.add_column('Status', key='status')

        self._all_pdfs = sorted(self._workspace.glob('*.pdf'))
        pdfs = self._apply_search(self._all_pdfs)

        for pdf in pdfs:
            processed = find_processed_files(self._workspace, pdf.name)
            if processed:
                drivers = ', '.join(p.driver_name for p in processed)
                pages = max(p.page_count for p in processed)
                status = f'processed via {drivers} · {pages} pages'
            else:
                status = 'not processed'
            table.add_row(pdf.name, status, key=str(pdf))

    def _apply_search(self, pdfs: list[Path]) -> list[Path]:
        if not self._search:
            return pdfs
        q = self._search.lower()
        return [p for p in pdfs if q in p.name.lower()]

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'file-list-search':
            self._search = event.value
            self._build_table()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value:
            self.focused_file = Path(str(event.row_key.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value:
            path = Path(str(event.row_key.value))
            self.focused_file = path
            self.post_message(self.FileSelected(path))

    def action_open_focused(self) -> None:
        if self.focused_file:
            self.post_message(self.FileSelected(self.focused_file))

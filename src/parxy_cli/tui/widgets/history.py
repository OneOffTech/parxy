"""History persistence and modal for recently opened workspaces."""

import json
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Input, Label


_HISTORY_PATH = Path.home() / '.parxy' / 'history.json'
_MAX_ENTRIES = 20


def load_history() -> list[dict]:
    """Return list of history entries [{path, date}], newest first."""
    if not _HISTORY_PATH.exists():
        return []
    try:
        return json.loads(_HISTORY_PATH.read_text(encoding='utf-8'))
    except Exception:
        return []


def save_to_history(path: Path) -> None:
    """Prepend *path* to history, capping the list at _MAX_ENTRIES."""
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = load_history()
    # Remove existing entry for same path so it bubbles to top.
    entries = [e for e in entries if e.get('path') != str(path)]
    entries.insert(0, {'path': str(path), 'date': datetime.now().strftime('%Y-%m-%d %H:%M')})
    entries = entries[:_MAX_ENTRIES]
    _HISTORY_PATH.write_text(json.dumps(entries, indent=2), encoding='utf-8')


class HistoryModal(ModalScreen):
    """Modal that lets the user pick a recently opened workspace."""

    BINDINGS = [Binding('escape', 'dismiss', 'Close')]

    DEFAULT_CSS = """
    HistoryModal {
        align: center middle;
    }

    #history-dialog {
        width: 70;
        height: 20;
        border: round $primary;
        background: $surface;
        layout: vertical;
        padding: 1 2;
    }

    #history-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #history-search {
        margin-bottom: 1;
    }

    #history-table {
        height: 1fr;
    }

    #history-hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._all_entries: list[dict] = load_history()

    def compose(self) -> ComposeResult:
        with Vertical(id='history-dialog'):
            yield Label('Recent Workspaces', id='history-title')
            yield Input(placeholder='Filter...', id='history-search', compact=True)
            yield DataTable(id='history-table', cursor_type='row')
            yield Label('Enter to open · Esc to close', id='history-hint')

    def on_mount(self) -> None:
        table = self.query_one('#history-table', DataTable)
        table.add_column('Date', key='date', width=18)
        table.add_column('Path', key='path')
        self._populate(self._all_entries)

    def _populate(self, entries: list[dict]) -> None:
        table = self.query_one('#history-table', DataTable)
        table.clear()
        for entry in entries:
            table.add_row(entry.get('date', ''), entry.get('path', ''), key=entry.get('path', ''))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'history-search':
            q = event.value.lower()
            filtered = [
                e for e in self._all_entries
                if q in e.get('path', '').lower() or q in e.get('date', '').lower()
            ]
            self._populate(filtered)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not (event.row_key and event.row_key.value):
            return
        path = Path(str(event.row_key.value))
        if path.is_dir():
            self.dismiss(path)
        else:
            hint = self.query_one('#history-hint', Label)
            hint.update(f'[red]Not found:[/red] {path}')

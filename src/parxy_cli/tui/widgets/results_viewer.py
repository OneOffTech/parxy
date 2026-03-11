"""Results viewer widget for displaying parser markdown outputs."""

from pathlib import Path
from typing import Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import MarkdownViewer, TabbedContent, TabPane

from parxy_core.models import Document


class ParserResults:
    """Store parsing results from different drivers."""

    def __init__(self):
        self.results: Dict[str, Document] = {}
        self.file_path: Optional[Path] = None

    def add_result(self, driver_name: str, document: Document):
        """Add a parsing result."""
        self.results[driver_name] = document

    def clear(self):
        """Clear all results."""
        self.results.clear()
        self.file_path = None

    def get_drivers(self) -> List[str]:
        """Get list of drivers that have results."""
        return list(self.results.keys())

    def get_json(self, driver_name: str) -> str:
        """Get JSON representation of a driver's result."""
        if driver_name in self.results:
            return self.results[driver_name].model_dump_json(indent=2)
        return ''

    def get_markdown(self, driver_name: str) -> str:
        """Get Markdown representation of a driver's result."""
        if driver_name in self.results:
            return self.results[driver_name].markdown()
        return ''


class ResultsViewer(Container):
    """Widget for displaying parser results."""

    def __init__(self, results: ParserResults, initial_tab: str = '', *args, **kwargs):
        self.results = results
        self.initial_tab = initial_tab
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the results viewer."""
        with TabbedContent(id='results-tabs', initial=self.initial_tab):
            for driver in self.results.get_drivers():
                with TabPane(driver, id=f'tab-{driver}'):
                    yield MarkdownViewer(
                        self.results.get_markdown(driver),
                        show_table_of_contents=False,
                    )

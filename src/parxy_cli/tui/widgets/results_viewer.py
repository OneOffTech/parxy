"""Results viewer widgets for displaying parser outputs and comparisons."""

import difflib
from pathlib import Path
from typing import Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Label, Static, TabbedContent, TabPane

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


class DiffViewer(Container):
    """Widget for displaying diffs between parser results."""

    def __init__(
        self, results: ParserResults, diff_type: str = 'json', *args, **kwargs
    ):
        self.results = results
        self.diff_type = diff_type
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the diff viewer."""
        with VerticalScroll(id='diff-container'):
            yield Static(self.generate_diff(), id='diff-content')

    def generate_diff(self) -> str:
        """Generate diff between parser results."""
        drivers = self.results.get_drivers()

        if len(drivers) < 2:
            return 'Select at least 2 parsers to see differences.'

        # Generate pairwise comparisons for all parsers
        all_diffs = []

        for i in range(len(drivers)):
            for j in range(i + 1, len(drivers)):
                driver1, driver2 = drivers[i], drivers[j]

                all_diffs.append(f'\n{"=" * 80}')
                all_diffs.append(f'Comparing: {driver1} vs {driver2}')
                all_diffs.append(f'{"=" * 80}\n')

                if self.diff_type == 'json':
                    content1 = self.results.get_json(driver1).splitlines(keepends=True)
                    content2 = self.results.get_json(driver2).splitlines(keepends=True)
                else:  # markdown
                    content1 = self.results.get_markdown(driver1).splitlines(
                        keepends=True
                    )
                    content2 = self.results.get_markdown(driver2).splitlines(
                        keepends=True
                    )

                diff = difflib.unified_diff(
                    content1,
                    content2,
                    fromfile=f'{driver1}',
                    tofile=f'{driver2}',
                    lineterm='',
                )

                diff_result = ''.join(diff)
                if diff_result:
                    all_diffs.append(diff_result)
                else:
                    all_diffs.append('No differences found.')

                all_diffs.append('\n')

        return ''.join(all_diffs) if all_diffs else 'No comparisons available.'

    def update_diff(self):
        """Update the diff content."""
        diff_static = self.query_one('#diff-content', Static)
        diff_static.update(self.generate_diff())


class SideBySideViewer(Container):
    """Widget for displaying parser results side-by-side."""

    def __init__(
        self, results: ParserResults, content_type: str = 'json', *args, **kwargs
    ):
        self.results = results
        self.content_type = content_type
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the side-by-side viewer."""
        drivers = self.results.get_drivers()

        if not drivers:
            yield Static('No results to display. Parse a file first.')
            return

        with Horizontal(id='side-by-side-container'):
            for driver in drivers:
                with Vertical(classes='parser-column'):
                    yield Label(f'[bold]{driver}[/bold]', classes='parser-title')
                    with VerticalScroll(classes='parser-content'):
                        if self.content_type == 'json':
                            yield Static(self.results.get_json(driver))
                        else:  # markdown
                            yield Static(self.results.get_markdown(driver))


class ResultsViewer(Container):
    """Widget for displaying parser results."""

    def __init__(self, results: ParserResults, *args, **kwargs):
        self.results = results
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the results viewer."""
        with TabbedContent(id='results-tabs'):
            # Side-by-side comparison views
            with TabPane('JSON Side-by-Side', id='json-sidebyside-tab'):
                yield SideBySideViewer(self.results, content_type='json')

            with TabPane('Markdown Side-by-Side', id='markdown-sidebyside-tab'):
                yield SideBySideViewer(self.results, content_type='markdown')

            # Diff views
            with TabPane('JSON Diff', id='json-diff-tab'):
                yield DiffViewer(self.results, diff_type='json')

            with TabPane('Markdown Diff', id='markdown-diff-tab'):
                yield DiffViewer(self.results, diff_type='markdown')

            # Individual parser results
            for driver in self.results.get_drivers():
                with TabPane(f'{driver} (JSON)', id=f'tab-{driver}-json'):
                    with VerticalScroll():
                        yield Static(self.results.get_json(driver))

                with TabPane(f'{driver} (MD)', id=f'tab-{driver}-md'):
                    with VerticalScroll():
                        yield Static(self.results.get_markdown(driver))

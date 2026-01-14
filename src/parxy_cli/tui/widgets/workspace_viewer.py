"""Workspace viewer widget for displaying pre-processed parsing results."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import (
    DataTable,
    Label,
    Static,
    TabbedContent,
    TabPane,
    MarkdownViewer,
)

from parxy_core.models import Document


@dataclass
class ProcessedFileInfo:
    """Information about a processed file result."""

    driver_name: str
    json_path: Path
    page_count: int
    cost_estimation: Optional[float]
    cost_estimation_unit: Optional[str]
    driver_elapsed_time: Optional[float]
    document: Optional[Document] = None


def find_processed_files(workspace: Path, pdf_filename: str) -> list[ProcessedFileInfo]:
    """Find all processed JSON files for a given PDF.

    Args:
        workspace: Path to the workspace directory
        pdf_filename: Name of the PDF file (e.g., "km-f.pdf")

    Returns:
        List of ProcessedFileInfo for each driver that processed this file
    """
    # Get the base name without extension
    base_name = Path(pdf_filename).stem

    # Pattern: {base_name}-{driver}.json
    pattern = re.compile(rf'^{re.escape(base_name)}-(.+)\.json$')

    results = []
    for json_file in workspace.glob(f'{base_name}-*.json'):
        match = pattern.match(json_file.name)
        if match:
            driver_name = match.group(1)

            # Load and parse the JSON file
            try:
                with open(json_file, encoding='utf-8') as f:
                    data = json.load(f)

                # Extract metadata
                pages = data.get('pages', [])
                parsing_metadata = data.get('parsing_metadata', {}) or {}

                info = ProcessedFileInfo(
                    driver_name=driver_name,
                    json_path=json_file,
                    page_count=len(pages),
                    cost_estimation=parsing_metadata.get('cost_estimation'),
                    cost_estimation_unit=parsing_metadata.get('cost_estimation_unit'),
                    driver_elapsed_time=parsing_metadata.get('driver_elapsed_time'),
                )
                results.append(info)
            except (json.JSONDecodeError, OSError):
                # Skip files that can't be read or parsed
                continue

    # Sort by driver name for consistent display
    results.sort(key=lambda x: x.driver_name)
    return results


def load_document(json_path: Path) -> Optional[Document]:
    """Load a Document from a JSON file.

    Args:
        json_path: Path to the JSON file

    Returns:
        Document instance or None if loading fails
    """
    try:
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
        return Document.model_validate(data)
    except (json.JSONDecodeError, OSError, ValueError):
        return None


class WorkspaceViewer(Container):
    """Widget for viewing pre-processed workspace results."""

    class DriverSelected(Message):
        """Message sent when a driver is selected from the table."""

        def __init__(self, info: ProcessedFileInfo) -> None:
            self.info = info
            super().__init__()

    def __init__(
        self,
        workspace: Path,
        pdf_filename: str,
        *args,
        **kwargs,
    ):
        self.workspace = workspace
        self.pdf_filename = pdf_filename
        self.processed_files: list[ProcessedFileInfo] = []
        self._selected_info: Optional[ProcessedFileInfo] = None
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the workspace viewer."""
        # Find processed files
        self.processed_files = find_processed_files(self.workspace, self.pdf_filename)

        with Vertical(id='workspace-viewer-container'):
            yield Label(
                f'[bold]Processed Results: {self.pdf_filename}[/bold]',
                classes='section-title',
            )

            if not self.processed_files:
                yield Static(
                    f'No processed files found for {self.pdf_filename}.\n'
                    'Process the file first using the parser selector.',
                    id='no-results-message',
                )
                return

            # Summary table with all drivers
            yield Label('[bold]Driver Comparison[/bold]', classes='subsection-title')
            yield DataTable(id='driver-comparison-table', cursor_type='row')

            # Tabbed content for detailed view per driver
            with TabbedContent(id='driver-tabs'):
                for info in self.processed_files:
                    # Load document for detailed view
                    doc = load_document(info.json_path)
                    info.document = doc

                    with TabPane(info.driver_name, id=f'tab-{info.driver_name}'):
                        with VerticalScroll():
                            if doc:
                                yield MarkdownViewer(
                                    doc.markdown(),
                                    show_table_of_contents=False,
                                )
                            else:
                                yield Static(f'Failed to load {info.json_path.name}')

    def on_mount(self) -> None:
        """Initialize the data table when mounted."""
        if not self.processed_files:
            return

        table = self.query_one('#driver-comparison-table', DataTable)

        # Add columns
        table.add_column('Driver', key='driver')
        table.add_column('Pages', key='pages')
        table.add_column('Cost', key='cost')
        table.add_column('Unit', key='unit')
        table.add_column('Time (s)', key='time')

        # Add rows for each driver
        for info in self.processed_files:
            cost_str = (
                f'{info.cost_estimation:.2f}'
                if info.cost_estimation is not None
                else '-'
            )
            unit_str = info.cost_estimation_unit or '-'
            time_str = (
                f'{info.driver_elapsed_time / 1000:.2f}'
                if info.driver_elapsed_time is not None
                else '-'
            )

            table.add_row(
                info.driver_name,
                str(info.page_count),
                cost_str,
                unit_str,
                time_str,
                key=info.driver_name,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the driver table."""
        driver_name = str(event.row_key.value)

        # Find the corresponding info
        for info in self.processed_files:
            if info.driver_name == driver_name:
                self._selected_info = info
                self.post_message(self.DriverSelected(info))
                break


class WorkspaceSummary(Container):
    """Widget showing summary of all processed files in workspace."""

    def __init__(self, workspace: Path, *args, **kwargs):
        self.workspace = workspace
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the workspace summary."""
        # Find all PDFs in workspace
        pdf_files = list(self.workspace.glob('*.pdf'))

        with Vertical(id='workspace-summary-container'):
            yield Label('[bold]Workspace Summary[/bold]', classes='section-title')

            if not pdf_files:
                yield Static('No PDF files found in workspace.')
                return

            yield DataTable(id='workspace-summary-table', cursor_type='row')

    def on_mount(self) -> None:
        """Initialize the summary table."""
        pdf_files = list(self.workspace.glob('*.pdf'))
        if not pdf_files:
            return

        table = self.query_one('#workspace-summary-table', DataTable)

        # Add columns
        table.add_column('File', key='file')
        table.add_column('Drivers', key='drivers')

        # Add rows for each PDF
        for pdf_file in sorted(pdf_files):
            processed = find_processed_files(self.workspace, pdf_file.name)
            driver_names = (
                ', '.join(info.driver_name for info in processed) if processed else '-'
            )

            table.add_row(
                pdf_file.name,
                driver_names,
                key=pdf_file.name,
            )

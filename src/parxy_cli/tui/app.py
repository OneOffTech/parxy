"""Main TUI application for Parxy parser comparison."""

import difflib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    DirectoryTree,
    Footer,
    Header,
    Label,
    Static,
    TabbedContent,
    TabPane,
)
from textual.binding import Binding
from textual.message import Message

from parxy_core.facade import Parxy
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
        return ""

    def get_markdown(self, driver_name: str) -> str:
        """Get Markdown representation of a driver's result."""
        if driver_name in self.results:
            return self.results[driver_name].markdown()
        return ""


class ParserSelector(Container):
    """Widget for selecting parsers."""

    class ParsersSelected(Message):
        """Message sent when parsers are selected and parse is requested."""

        def __init__(self, selected_parsers: List[str]) -> None:
            self.selected_parsers = selected_parsers
            super().__init__()

    def compose(self) -> ComposeResult:
        """Compose the parser selector."""
        with Vertical(id="parser-selector-container"):
            yield Label("Select Parsers (2+ for comparison):", classes="section-title")
            
            # Scrollable area for checkboxes
            with VerticalScroll(id="parser-checkboxes-scroll"):
                # Get available drivers
                drivers = Parxy._get_factory().get_supported_drivers()
                
                for driver in drivers:
                    yield Checkbox(driver, id=f"parser-{driver}")
            
            # Button outside scroll area - always visible
            yield Button("Parse Selected File", id="parse-button", variant="primary")

    def get_selected_parsers(self) -> List[str]:
        """Get list of selected parser names."""
        selected = []
        for checkbox in self.query(Checkbox):
            if checkbox.value:
                parser_name = str(checkbox.id).replace("parser-", "")
                selected.append(parser_name)
        return selected


class DiffViewer(Container):
    """Widget for displaying diffs between parser results."""

    def __init__(self, results: ParserResults, diff_type: str = "json"):
        self.results = results
        self.diff_type = diff_type
        super().__init__()

    def compose(self) -> ComposeResult:
        """Compose the diff viewer."""
        with VerticalScroll(id="diff-container"):
            yield Static(self.generate_diff(), id="diff-content")

    def generate_diff(self) -> str:
        """Generate diff between parser results."""
        drivers = self.results.get_drivers()
        
        if len(drivers) < 2:
            return "Select at least 2 parsers to see differences."
        
        # Generate pairwise comparisons for all parsers
        all_diffs = []
        
        for i in range(len(drivers)):
            for j in range(i + 1, len(drivers)):
                driver1, driver2 = drivers[i], drivers[j]
                
                all_diffs.append(f"\n{'='*80}")
                all_diffs.append(f"Comparing: {driver1} vs {driver2}")
                all_diffs.append(f"{'='*80}\n")
                
                if self.diff_type == "json":
                    content1 = self.results.get_json(driver1).splitlines(keepends=True)
                    content2 = self.results.get_json(driver2).splitlines(keepends=True)
                else:  # markdown
                    content1 = self.results.get_markdown(driver1).splitlines(keepends=True)
                    content2 = self.results.get_markdown(driver2).splitlines(keepends=True)
                
                diff = difflib.unified_diff(
                    content1,
                    content2,
                    fromfile=f"{driver1}",
                    tofile=f"{driver2}",
                    lineterm="",
                )
                
                diff_result = "".join(diff)
                if diff_result:
                    all_diffs.append(diff_result)
                else:
                    all_diffs.append("No differences found.")
                
                all_diffs.append("\n")
        
        return "".join(all_diffs) if all_diffs else "No comparisons available."

    def update_diff(self):
        """Update the diff content."""
        diff_static = self.query_one("#diff-content", Static)
        diff_static.update(self.generate_diff())


class SideBySideViewer(Container):
    """Widget for displaying parser results side-by-side."""

    def __init__(self, results: ParserResults, content_type: str = "json"):
        self.results = results
        self.content_type = content_type
        super().__init__()

    def compose(self) -> ComposeResult:
        """Compose the side-by-side viewer."""
        drivers = self.results.get_drivers()
        
        if not drivers:
            yield Static("No results to display. Parse a file first.")
            return
        
        with Horizontal(id="side-by-side-container"):
            for driver in drivers:
                with Vertical(classes="parser-column"):
                    yield Label(f"[bold]{driver}[/bold]", classes="parser-title")
                    with VerticalScroll(classes="parser-content"):
                        if self.content_type == "json":
                            yield Static(self.results.get_json(driver))
                        else:  # markdown
                            yield Static(self.results.get_markdown(driver))


class ResultsViewer(Container):
    """Widget for displaying parser results."""

    def __init__(self, results: ParserResults):
        self.results = results
        super().__init__()

    def compose(self) -> ComposeResult:
        """Compose the results viewer."""
        with TabbedContent(id="results-tabs"):
            # Side-by-side comparison views
            with TabPane("JSON Side-by-Side", id="json-sidebyside-tab"):
                yield SideBySideViewer(self.results, content_type="json")
            
            with TabPane("Markdown Side-by-Side", id="markdown-sidebyside-tab"):
                yield SideBySideViewer(self.results, content_type="markdown")
            
            # Diff views
            with TabPane("JSON Diff", id="json-diff-tab"):
                yield DiffViewer(self.results, diff_type="json")
            
            with TabPane("Markdown Diff", id="markdown-diff-tab"):
                yield DiffViewer(self.results, diff_type="markdown")
            
            # Individual parser results
            for driver in self.results.get_drivers():
                with TabPane(f"{driver} (JSON)", id=f"tab-{driver}-json"):
                    with VerticalScroll():
                        yield Static(self.results.get_json(driver))
                
                with TabPane(f"{driver} (MD)", id=f"tab-{driver}-md"):
                    with VerticalScroll():
                        yield Static(self.results.get_markdown(driver))


class FileTreeWithFilter(DirectoryTree):
    """Directory tree that filters for document files."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc', '.html', '.htm', '.xml'}

    def filter_paths(self, paths):
        """Filter to show only directories and supported document files."""
        return [
            path for path in paths
            if path.is_dir() or path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]


class ParxyTUI(App):
    """A Textual app for comparing Parxy parsers."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 3fr;
        grid-rows: auto 1fr;
    }

    Header {
        column-span: 2;
    }

    #sidebar {
        row-span: 1;
        width: 100%;
        height: 100%;
        border: solid $primary;
        layout: vertical;
    }

    #file-tree-section {
        height: 1fr;
        width: 100%;
        overflow-y: auto;
    }

    #file-tree {
        height: auto;
    }

    #parser-selector {
        height: auto;
        border-top: solid $primary;
        background: $surface;
    }

    #main-content {
        row-span: 1;
        column-span: 1;
        width: 100%;
        height: 100%;
        border: solid $secondary;
    }

    #parser-selector-container {
        height: auto;
        layout: vertical;
        padding: 1 0;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        padding: 0 2;
        margin-bottom: 1;
    }

    #parser-checkboxes-scroll {
        max-height: 15;
        width: 100%;
        padding: 0 2;
    }

    #parse-button {
        margin: 1 2;
        width: auto;
    }

    #status-bar {
        background: $panel;
        color: $text;
        padding: 1 2;
        height: auto;
    }

    #diff-container {
        width: 100%;
        height: 100%;
    }

    #diff-content {
        padding: 1 2;
    }

    Checkbox {
        margin: 0 0 0 2;
    }

    #side-by-side-container {
        width: 100%;
        height: 100%;
    }

    .parser-column {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        margin: 0 1;
    }

    .parser-title {
        background: $primary;
        color: $text;
        text-align: center;
        padding: 1;
        text-style: bold;
    }

    .parser-content {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", key_display="Ctrl+Q"),
        Binding("ctrl+r", "refresh", "Refresh", key_display="Ctrl+R"),
        Binding("ctrl+c", "request_quit", "Quit (press twice)", key_display="Ctrl+C", show=False),
    ]

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.results = ParserResults()
        self.current_file: Optional[Path] = None
        self._last_ctrl_c_time: float = 0
        self._ctrl_c_window: float = 2.0  # seconds
        super().__init__()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with Vertical(id="sidebar"):
            # File tree section (scrollable)
            with Container(id="file-tree-section"):
                yield Label("Workspace Files:", classes="section-title")
                yield FileTreeWithFilter(str(self.workspace), id="file-tree")
            
            # Parser selector section (fixed at bottom)
            yield ParserSelector(id="parser-selector")
        
        with Vertical(id="main-content"):
            yield Static("Select a file and parsers to begin", id="status-bar")
            yield ResultsViewer(self.results)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection from the tree."""
        self.current_file = event.path
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(f"Selected: {self.current_file.name}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "parse-button":
            self.parse_file()

    def parse_file(self) -> None:
        """Parse the selected file with selected parsers."""
        if not self.current_file:
            status_bar = self.query_one("#status-bar", Static)
            status_bar.update("[bold red]ERROR:[/bold red] Please select a file first!")
            return

        parser_selector = self.query_one("#parser-selector", ParserSelector)
        selected_parsers = parser_selector.get_selected_parsers()

        if len(selected_parsers) < 1:
            status_bar = self.query_one("#status-bar", Static)
            status_bar.update("[bold red]ERROR:[/bold red] Please select at least one parser!")
            return

        # Clear previous results
        self.results.clear()
        self.results.file_path = self.current_file

        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(f"[bold yellow]PARSING:[/bold yellow] {self.current_file.name} with {len(selected_parsers)} parser(s)...")

        # Parse with each selected parser
        errors = []
        success_count = 0
        for parser_name in selected_parsers:
            try:
                status_bar.update(f"[bold yellow]PARSING:[/bold yellow] {parser_name}...")
                doc = Parxy.parse(
                    file=str(self.current_file),
                    driver_name=parser_name,
                    level="page",
                )
                self.results.add_result(parser_name, doc)
                success_count += 1
            except Exception as e:
                error_detail = str(e)
                # Truncate long error messages
                if len(error_detail) > 100:
                    error_detail = error_detail[:97] + "..."
                errors.append(f"{parser_name}: {error_detail}")

        # Update status with rich formatting
        if errors and success_count == 0:
            error_msg = "; ".join(errors)
            status_bar.update(f"[bold red]FAILED:[/bold red] All parsers failed. {error_msg}")
        elif errors:
            error_msg = "; ".join(errors)
            status_bar.update(
                f"[bold yellow]PARTIAL:[/bold yellow] {success_count}/{len(selected_parsers)} succeeded. Errors: {error_msg}"
            )
        else:
            status_bar.update(
                f"[bold green]SUCCESS:[/bold green] Parsed {self.current_file.name} with {len(selected_parsers)} parser(s)"
            )

        # Refresh the results viewer
        self.refresh_results_viewer()

    def refresh_results_viewer(self) -> None:
        """Refresh the results viewer with new data."""
        # Remove old results viewer and create a new one
        old_viewer = self.query_one(ResultsViewer)
        old_viewer.remove()
        
        main_content = self.query_one("#main-content", Vertical)
        main_content.mount(ResultsViewer(self.results))

    def action_refresh(self) -> None:
        """Refresh the file tree."""
        file_tree = self.query_one("#file-tree", FileTreeWithFilter)
        file_tree.reload()

    def action_request_quit(self) -> None:
        """Handle Ctrl+C - require pressing twice within time window to quit."""
        current_time = time.time()
        time_since_last = current_time - self._last_ctrl_c_time
        
        if time_since_last <= self._ctrl_c_window:
            # Second Ctrl+C within window - quit
            self.exit()
        else:
            # First Ctrl+C - show message
            self._last_ctrl_c_time = current_time
            status_bar = self.query_one("#status-bar", Static)
            status_bar.update(
                f"[bold yellow]Press Ctrl+C again within {self._ctrl_c_window:.0f}s to quit, or use Ctrl+Q[/bold yellow]"
            )


def run_tui(workspace: Path):
    """Run the TUI application."""
    app = ParxyTUI(workspace)
    app.run()

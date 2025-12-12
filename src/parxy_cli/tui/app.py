"""Main TUI application for Parxy parser comparison."""

import time
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Header, Static
from textual.binding import Binding

from parxy_core.facade import Parxy
from parxy_cli.tui.widgets import (
    FileTreeSelector,
    FilteredDirectoryTree,
    ParserSelector,
    ParserResults,
    ResultsViewer,
)


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

    #file-tree-selector {
        height: 100%;
    }

    #file-tree-selector-container {
        height: 100%;
        layout: vertical;
    }

    #file-search-input {
        margin: 0 2 1 2;
    }

    #file-tree {
        height: 1fr;
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
                yield FileTreeSelector(self.workspace, id="file-tree-selector")
            
            # Parser selector section (fixed at bottom)
            yield ParserSelector(id="parser-selector")
        
        with Vertical(id="main-content"):
            yield Static("Select a file and parsers to begin", id="status-bar")
            yield ResultsViewer(self.results)

    def on_file_tree_selector_file_selected(self, event: FileTreeSelector.FileSelected) -> None:
        """Handle file selection from the tree selector widget."""
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
        file_tree = self.query_one("#file-tree", FilteredDirectoryTree)
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

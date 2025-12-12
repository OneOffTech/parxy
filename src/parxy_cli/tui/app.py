"""Main TUI application for Parxy parser comparison."""

import time
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Header, Static
from textual.binding import Binding

from parxy_core.facade import Parxy
from parxy_cli.tui.widgets import (
    FileTreeSelector,
    FilteredDirectoryTree,
    ParserSelector,
    ParserResults,
    ResultsViewer,
    WelcomeScreen,
)


class ParxyTUI(App):
    """A Textual app for comparing Parxy parsers."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 2fr 1fr;
        padding: 1 2;
    }

    Header {
        column-span: 2;
    }

    /* Main area - left side, 2/3 width */
    #main-area {
        width: 100%;
        height: 100%;
        layout: vertical;
        padding: 0 2 0 0;
    }

    #main-content-container {
        height: 1fr;
        width: 100%;
    }

    #results-viewer {
        height: 1fr;
        width: 100%;
        display: none;
    }

    #status-container {
        height: auto;
        width: 100%;
        padding: 1 0;
        dock: bottom;
        layout: horizontal;
    }

    #status-bar {
        width: 1fr;
        height: auto;
        color: $text-muted;
        content-align: left middle;
    }

    #new-parse-button {
        width: auto;
        min-width: 16;
        display: none;
    }

    #command-hint {
        width: auto;
        height: auto;
        color: $text-muted;
        text-style: italic;
        content-align: right middle;
        padding: 0 1;
    }

    /* Sidebar - right side, 1/3 width */
    #sidebar {
        width: 100%;
        height: 100%;
        layout: vertical;
        padding: 0 0 0 2;
        border-left: solid $primary;
    }

    #file-tree-selector {
        height: 1fr;
    }

    #file-tree-selector-container {
        height: 100%;
        layout: vertical;
    }

    #file-search-input {
        margin: 0 0 1 0;
    }

    #file-tree {
        height: 1fr;
    }

    #workspace-footer {
        height: auto;
        padding: 1 0;
        color: $text-muted;
        text-style: italic;
        dock: bottom;
    }

    /* Welcome screen */
    #welcome-container {
        height: 100%;
        width: 100%;
        align: center middle;
    }

    #welcome-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 2;
    }

    #welcome-message {
        text-align: center;
        color: $text-muted;
        padding: 1 4;
    }

    /* Parser selector */
    #parser-selector {
        height: auto;
        padding: 2 0;
    }

    #parser-selector-container {
        height: auto;
        layout: vertical;
    }

    .section-title {
        text-style: bold;
        padding: 0 0 1 0;
    }

    #parser-checkboxes-scroll {
        max-height: 12;
        width: 100%;
    }

    #parse-button {
        margin: 2 0 0 0;
        width: auto;
    }

    Checkbox {
        margin: 0 0 0 2;
    }

    /* Results viewer */
    #diff-container {
        width: 100%;
        height: 100%;
    }

    #diff-content {
        padding: 1;
    }

    #side-by-side-container {
        width: 100%;
        height: 100%;
    }

    .parser-column {
        width: 1fr;
        height: 100%;
        margin: 0 1;
    }

    .parser-title {
        background: $boost;
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
        Binding("ctrl+r", "refresh", "Refresh file tree", key_display="Ctrl+R"),
        Binding("ctrl+n", "new_parse", "New parse", key_display="Ctrl+N"),
        Binding("ctrl+s", "start_parse", "Start parsing", key_display="Ctrl+S"),
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
        
        # Main area (left side, 2/3 width)
        with Vertical(id="main-area"):
            # Welcome/Parser selector section
            with Container(id="main-content-container"):
                yield WelcomeScreen(id="welcome-screen")
                yield ParserSelector(id="parser-selector")
            
            # Results viewer (initially hidden)
            yield ResultsViewer(self.results, id="results-viewer")
            
            # Status footer at bottom of main area
            with Horizontal(id="status-container"):
                yield Static("Ready", id="status-bar")
                yield Button("New Parse", id="new-parse-button", variant="default")
                yield Static("Ctrl+P: Commands", id="command-hint")
        
        # Sidebar (right side, 1/3 width)
        with Vertical(id="sidebar"):
            # File tree at top
            yield FileTreeSelector(self.workspace, id="file-tree-selector")
            
            # Workspace path footer at bottom
            yield Static(f"Workspace: {self.workspace}", id="workspace-footer")

    def on_file_tree_selector_file_selected(self, event: FileTreeSelector.FileSelected) -> None:
        """Handle file selection from the tree selector widget."""
        self.current_file = event.path
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(f"File selected: {self.current_file.name}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "parse-button":
            self.run_worker(self.parse_file())
        elif event.button.id == "new-parse-button":
            self.action_new_parse()

    async def parse_file(self) -> None:
        """Parse the selected file with selected parsers."""
        status_bar = self.query_one("#status-bar", Static)
        parse_button = self.query_one("#parse-button", Button)
        
        if not self.current_file:
            status_bar.update("Error: Please select a file first!")
            return

        parser_selector = self.query_one("#parser-selector", ParserSelector)
        selected_parsers = parser_selector.get_selected_parsers()

        if len(selected_parsers) < 1:
            status_bar.update("Error: Please select at least one parser!")
            return

        # Disable button during processing
        parse_button.disabled = True
        
        # Show initial processing message
        status_bar.update(f"Processing... Preparing to parse {self.current_file.name}")

        # Hide welcome screen and show results viewer
        self.query_one("#main-content-container").styles.display = "none"
        self.query_one("#results-viewer").styles.display = "block"

        # Clear previous results
        self.results.clear()
        self.results.file_path = self.current_file

        # Parse with each selected parser
        errors = []
        success_count = 0
        total_parsers = len(selected_parsers)
        
        for idx, parser_name in enumerate(selected_parsers, 1):
            try:
                # Show progress status
                status_bar.update(f"Processing... [{idx}/{total_parsers}] Parsing with {parser_name}")
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

        # Show refreshing message
        status_bar.update("Processing... Refreshing results view")
        
        # Refresh the results viewer
        await self.refresh_results_viewer()
        
        # Re-enable parse button and show new parse button
        parse_button.disabled = False
        new_parse_button = self.query_one("#new-parse-button", Button)
        new_parse_button.styles.display = "block"
        
        # Update final status
        if errors and success_count == 0:
            error_msg = "; ".join(errors)
            status_bar.update(f"Failed: All parsers failed. {error_msg}")
        elif errors:
            error_msg = "; ".join(errors)
            status_bar.update(
                f"Completed with errors: {success_count}/{total_parsers} succeeded. Errors: {error_msg}"
            )
        else:
            status_bar.update(
                f"Complete: Successfully parsed {self.current_file.name} with {total_parsers} parser(s)"
            )

    async def refresh_results_viewer(self) -> None:
        """Refresh the results viewer with new data."""
        # Remove old results viewer
        old_viewer = self.query_one("#results-viewer", ResultsViewer)
        await old_viewer.remove()
        
        # Create and mount new viewer with updated results
        main_area = self.query_one("#main-area", Vertical)
        new_viewer = ResultsViewer(self.results, id="results-viewer")
        new_viewer.styles.display = "block"
        await main_area.mount(new_viewer, before="#status-bar")

    def action_refresh(self) -> None:
        """Refresh file tree - Reload the file list from the workspace."""
        file_tree = self.query_one("#file-tree", FilteredDirectoryTree)
        file_tree.reload()
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update("File tree refreshed")

    def action_start_parse(self) -> None:
        """Start parsing - Parse the selected file with chosen parsers."""
        self.run_worker(self.parse_file())

    def action_new_parse(self) -> None:
        """New parse - Return to welcome screen while keeping file selection."""
        # Show welcome screen and hide results viewer
        self.query_one("#main-content-container").styles.display = "block"
        self.query_one("#results-viewer").styles.display = "none"
        
        # Clear results but keep file selection
        self.results.clear()
        
        # Reset button states
        parse_button = self.query_one("#parse-button", Button)
        parse_button.disabled = False
        
        new_parse_button = self.query_one("#new-parse-button", Button)
        new_parse_button.styles.display = "none"
        
        # Update status
        status_bar = self.query_one("#status-bar", Static)
        if self.current_file:
            status_bar.update(f"Ready for new parse. File selected: {self.current_file.name}")
        else:
            status_bar.update("Ready for new parse. Select a file to begin.")

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
                f"Press Ctrl+C again within {self._ctrl_c_window:.0f}s to quit, or use Ctrl+Q"
            )


def run_tui(workspace: Path):
    """Run the TUI application."""
    app = ParxyTUI(workspace)
    app.run()

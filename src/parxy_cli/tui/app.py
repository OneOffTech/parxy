"""Main TUI application for Parxy parser comparison."""

import time
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.command import Provider
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
    Footer,
    WelcomeContainer,
)


class ParxyTUI(App):
    """Exploring document parsers."""

    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", key_display="Ctrl+Q"),
        Binding("ctrl+r", "refresh", "Refresh file tree", key_display="Ctrl+R"),
        Binding("ctrl+n", "new_parse", "New parse", key_display="Ctrl+N"),
        Binding("ctrl+s", "start_parse", "Start parsing", key_display="Ctrl+S"),
        Binding("ctrl+b", "toggle_sidebar", "Toggle sidebar", key_display="Ctrl+B"),
        Binding("ctrl+c", "request_quit", "Quit (press twice)", key_display="Ctrl+C", show=False),
    ]

    def __init__(self, workspace: Path):
        super().__init__()
        self.workspace = workspace
        self.results = ParserResults()
        self.current_file: Optional[Path] = None
        self._last_ctrl_c_time: float = 0
        self._ctrl_c_window: float = 2.0  # seconds
        self._sidebar_visible: bool = True  # Track sidebar visibility
        self.theme = "flexoki"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        # Main area (left side, 2/3 width)
        with Vertical(id="main-area", classes="p-1"):
            # Welcome container (logo, welcome message, parser selector)
            yield WelcomeContainer(id="welcome-container")
            
            # Results viewer (initially hidden)
            yield ResultsViewer(self.results, id="results-viewer")
            
            yield Footer()
        
        # # Sidebar (right side, 1/3 width)
        with Vertical(id="sidebar", classes="sidebar"):
            # File tree at top
            yield FileTreeSelector(self.workspace, id="file-tree-selector")
            
            # Workspace path footer at bottom
            yield Static(f"{self.workspace}", classes="doc-bottom pt-1") # id="workspace-footer", 
            yield Static(f"[$primary]▣[/$primary] parxy", classes="doc-bottom pt-1")

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
        
        # Force UI refresh to show status immediately
        self.refresh()

        # Hide welcome container and show results viewer
        self.query_one("#welcome-container").display = False
        self.query_one("#results-viewer").display = True

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
                self.refresh()  # Force UI update to show progress
                
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
        self.refresh()  # Force UI update
        
        # Refresh the results viewer
        await self.refresh_results_viewer()
        
        # Re-enable parse button and show new parse button
        parse_button.disabled = False
        
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
                f"Parsed {self.current_file.name} with {total_parsers} parser{"s" if total_parsers > 1 else ""}"
            )

    async def refresh_results_viewer(self) -> None:
        """Refresh the results viewer with new data."""
        # Remove old results viewer and create new one
        old_viewer = self.query_one("#results-viewer", ResultsViewer)
        await old_viewer.remove()
        
        # Create and mount new viewer with updated results
        main_area = self.query_one("#main-area", Vertical)
        new_viewer = ResultsViewer(self.results, id="results-viewer")
        new_viewer.display = True
        await main_area.mount(new_viewer, before="Footer")

    def action_refresh(self) -> None:
        """Refresh file tree."""
        file_tree = self.query_one("#file-tree", FilteredDirectoryTree)
        file_tree.reload()
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update("File tree refreshed")

    def action_start_parse(self) -> None:
        """Start parsing the selected file."""
        self.run_worker(self.parse_file())

    def action_new_parse(self) -> None:
        """Start a new parse (return to parser selection)."""
        # Show welcome container and hide results viewer
        self.query_one("#welcome-container").display = True
        self.query_one("#results-viewer").display = False
        
        # Clear results but keep file selection
        self.results.clear()
        
        # Reset button states
        parse_button = self.query_one("#parse-button", Button)
        parse_button.disabled = False
        
        # Update status
        status_bar = self.query_one("#status-bar", Static)
        if self.current_file:
            status_bar.update(f"Ready for new parse. File selected: {self.current_file.name}")
        else:
            status_bar.update("Ready for new parse. Select a file to begin.")

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        sidebar = self.query_one("#sidebar")
        
        # Toggle visibility
        self._sidebar_visible = not self._sidebar_visible
        sidebar.display = self._sidebar_visible
        
        # Toggle screen layout class
        if self._sidebar_visible:
            self.screen.remove_class("sidebar-hidden")
        else:
            self.screen.add_class("sidebar-hidden")
        
        # Update status
        status_bar = self.query_one("#status-bar", Static)
        if self._sidebar_visible:
            status_bar.update("Sidebar shown")
        else:
            status_bar.update("Sidebar hidden - Main area expanded")

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

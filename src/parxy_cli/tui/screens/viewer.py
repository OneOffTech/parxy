"""Viewer screen - parser selector and results viewer."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from parxy_core.facade import Parxy
from parxy_cli.tui.widgets.footer import Footer
from parxy_cli.tui.widgets.header import ParxyHeader
from parxy_cli.tui.widgets.parser_selector import ParserSelector
from parxy_cli.tui.widgets.results_viewer import ParserResults, ResultsViewer
from parxy_cli.tui.widgets.welcome_container import WelcomeContainer
from parxy_cli.tui.widgets.workspace_viewer import find_processed_files, load_document


class ViewerScreen(Screen):
    """Screen for parsing and viewing a document's results."""

    DEFAULT_CSS = """
    ViewerScreen {
        layout: vertical;
    }

    #viewer-main {
        height: 1fr;
        width: 100%;
        layout: vertical;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding(
            'ctrl+e',
            'pop_screen',
            'Back to browse',
            key_display='Ctrl+E',
            priority=True,
        ),
        Binding(
            'ctrl+n', 'new_parse', 'New parse', key_display='Ctrl+N', priority=True
        ),
        Binding(
            'ctrl+s',
            'start_parse',
            'Start parsing',
            key_display='Ctrl+S',
            priority=True,
        ),
        Binding('ctrl+p', 'command_palette', 'Commands', show=False),
    ]

    def __init__(self, file_path: Path, workspace: Path, *args, **kwargs):
        self.current_file = file_path
        self.workspace = workspace
        self.results = ParserResults()
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield ParxyHeader(
            breadcrumb=f'{self.workspace.name} / {self.current_file.name}'
        )
        with Vertical(id='viewer-main'):
            yield WelcomeContainer(id='welcome-container')
            yield ResultsViewer(self.results, id='results-viewer')
        yield Footer()

    def on_mount(self) -> None:
        processed = find_processed_files(self.workspace, self.current_file.name)
        if processed:
            self.run_worker(self._load_processed_results(processed))
        else:
            self.query_one('#status-bar', Static).update(
                f'File: {self.current_file.name} — select parsers and press Ctrl+S'
            )

    # ------------------------------------------------------------------
    # Loading pre-processed results
    # ------------------------------------------------------------------

    async def _load_processed_results(self, processed) -> None:
        """Load pre-processed JSON results and display them immediately."""
        status = self.query_one('#status-bar', Static)
        status.update(f'Loading results for {self.current_file.name}...')

        for info in processed:
            doc = load_document(info.json_path)
            if doc is not None:
                self.results.add_result(info.driver_name, doc)

        self.query_one('#welcome-container').display = False
        await self._refresh_results_viewer()

        drivers = ', '.join(p.driver_name for p in processed)
        status.update(
            f'File: {self.current_file.name} | Drivers: {drivers} — Ctrl+N to re-parse'
        )

    # ------------------------------------------------------------------
    # Button presses (delegated from WelcomeContainer / ParserSelector)
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'parse-button':
            self.run_worker(self._parse_file())
        elif event.button.id == 'new-parse-button':
            self.action_new_parse()

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    async def _parse_file(self) -> None:
        status_bar = self.query_one('#status-bar', Static)
        parse_button = self.query_one('#parse-button', Button)
        parser_selector = self.query_one('#parser-selector', ParserSelector)

        selected_parsers = parser_selector.get_selected_parsers()
        if not selected_parsers:
            status_bar.update('Error: Please select at least one parser!')
            return

        parse_button.disabled = True
        status_bar.update(f'Preparing to parse {self.current_file.name}...')
        self.refresh()

        self.query_one('#welcome-container').display = False
        self.results.clear()
        self.results.file_path = self.current_file

        errors = []
        success_count = 0
        total = len(selected_parsers)

        for idx, parser_name in enumerate(selected_parsers, 1):
            try:
                status_bar.update(
                    f'Processing... [{idx}/{total}] Parsing with {parser_name}'
                )
                self.refresh()
                doc = Parxy.parse(
                    file=str(self.current_file),
                    driver_name=parser_name,
                    level='page',
                )
                self.results.add_result(parser_name, doc)
                success_count += 1
            except Exception as e:
                msg = str(e)
                if len(msg) > 100:
                    msg = msg[:97] + '...'
                errors.append(f'{parser_name}: {msg}')

        status_bar.update('Refreshing results...')
        self.refresh()
        await self._refresh_results_viewer()
        parse_button.disabled = False

        if errors and success_count == 0:
            status_bar.update(f'Failed: All parsers errored. {"; ".join(errors)}')
        elif errors:
            status_bar.update(
                f'Completed with errors: {success_count}/{total} succeeded. '
                f'Errors: {"; ".join(errors)}'
            )
        else:
            status_bar.update(
                f'Parsed {self.current_file.name} with '
                f'{total} parser{"s" if total > 1 else ""}'
            )

    async def _refresh_results_viewer(self) -> None:
        old = self.query_one('#results-viewer', ResultsViewer)
        await old.remove()
        main = self.query_one('#viewer-main', Vertical)
        new = ResultsViewer(self.results, id='results-viewer')
        new.display = True
        await main.mount(new)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_start_parse(self) -> None:
        self.run_worker(self._parse_file())

    def action_new_parse(self) -> None:
        self.query_one('#welcome-container').display = True
        self.query_one('#results-viewer').display = False
        self.results.clear()
        self.query_one('#parse-button', Button).disabled = False
        self.query_one('#status-bar', Static).update(
            f'File: {self.current_file.name} — select parsers and press Ctrl+S'
        )

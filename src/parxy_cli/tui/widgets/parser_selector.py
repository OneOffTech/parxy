"""Parser selector widget for choosing parsers to run."""

from typing import List

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Label
from textual.message import Message

from parxy_core.facade import Parxy


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

from textual.app import ComposeResult
from textual.widgets import Static
from textual.widget import Widget

LOGO_LINES = [
    "█▀▀▀█ █▀▀▀█ █▀▀▀█ █▄ ▄█ █░░░█",
    "█░░░█ █▀▀▀█ █▀▀█▀ ▄▄▀▄▄ ▀▀█▀▀",
    "█▀▀▀▀ ▀   ▀ ▀   ▀ ▀   ▀   ▀  "
]

class Logo(Widget):
    """A widget that displays the parxy logo."""
    
    DEFAULT_CSS = """
    Logo {
        width: 30;
        height: 3;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Compose the logo widget."""
        logo_text = ""
        for left in LOGO_LINES:
            logo_text += f"{left}\n"
        
        yield Static(logo_text.rstrip(), classes="logo")

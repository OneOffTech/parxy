"""
Flexoki-themed Console class for Rich library
Uses the warm, inky Flexoki color scheme by Steph Ango
"""

from rich.console import Console as RichConsole
from rich.theme import Theme
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.markdown import Markdown
from rich.panel import Panel
from contextlib import contextmanager


class Console:
    """
    A themed console wrapper using the Flexoki color scheme.
    Provides methods for styled output, progress bars, and spinners.
    """
    
    # Flexoki color palette (dark theme optimized)
    COLORS = {
        # Base colors
        'bg': '#1C1B1A',
        'bg_2': '#282726',
        'ui': '#343331',
        'ui_2': '#403E3C',
        'ui_3': '#575653',
        'tx_3': '#B7B5AC',
        'tx_2': '#CECDC3',
        'tx': '#E6E4D9',
        
        # Accent colors (400 series for dark theme)
        'red': '#D14D41',
        'orange': '#DA702C',
        'yellow': '#D0A215',
        'green': '#879A39',
        'cyan': '#3AA99F',
        'blue': '#4385BE',
        'purple': '#8B7EC8',
        'magenta': '#CE5D97',
    }
    
    def __init__(self):
        """Initialize the console with Flexoki theme."""
        self.theme = Theme({
            # Base text styles
            "default": f"{self.COLORS['tx']}",
            "muted": f"{self.COLORS['tx_2']}",
            "faint": f"{self.COLORS['tx_3']}",
            
            # Message types
            "success": f"bold {self.COLORS['green']}",
            "info": f"{self.COLORS['cyan']}",
            "warning": f"bold {self.COLORS['orange']}",
            "error": f"bold {self.COLORS['red']}",
            
            # Semantic colors
            "highlight": f"bold {self.COLORS['yellow']}",
            "link": f"underline {self.COLORS['blue']}",
            "code": f"{self.COLORS['purple']}",
            
            # Progress/spinner colors
            "progress.description": f"{self.COLORS['tx_2']}",
            "progress.percentage": f"{self.COLORS['cyan']}",
            "bar.complete": f"{self.COLORS['green']}",
            "bar.finished": f"{self.COLORS['cyan']}",
            "bar.pulse": f"{self.COLORS['blue']}",
        })
        
        self.console = RichConsole(theme=self.theme)
    
    def print(self, *args, style=None, **kwargs):
        """Print with optional style."""
        self.console.print(*args, style=style, **kwargs)
    
    def success(self, message: str, prefix: str = "✓"):
        """Print a success message."""
        self.console.print(f"[success]{prefix}[/success] {message}")
    
    def info(self, message: str, prefix: str = "ℹ"):
        """Print an info message."""
        self.console.print(f"[info]{prefix}[/info] {message}")
    
    def warning(self, message: str, prefix: str = "⚠"):
        """Print a warning message."""
        self.console.print(f"[warning]{prefix}[/warning] {message}")
    
    def error(self, message: str, prefix: str = "✗"):
        """Print an error message."""
        self.console.print(f"[error]{prefix}[/error] {message}")
    
    def muted(self, message: str):
        """Print muted text."""
        self.console.print(message, style="muted")
    
    def faint(self, message: str):
        """Print faint text."""
        self.console.print(message, style="faint")
    
    def highlight(self, message: str):
        """Print highlighted text."""
        self.console.print(message, style="highlight")
    
    def markdown(self, content: str):
        """Render markdown content."""
        md = Markdown(content)
        self.console.print(md)
    
    def panel(self, content: str, title: str = None, style: str = "default", border_style: str = None):
        """Display content in a panel."""
        border_color = border_style or self.COLORS['ui_2']
        panel = Panel(
            content,
            title=title,
            border_style=border_color,
            style=style
        )
        self.console.print(panel)
    
    def rule(self, title: str = None, style: str = None):
        """Print a horizontal rule."""
        rule_style = style or self.COLORS['ui_2']
        self.console.rule(title, style=rule_style)
    
    @contextmanager
    def progress(self, description: str = "Working..."):
        """
        Context manager for a progress bar.
        
        Usage:
            with console.progress("Processing files") as progress:
                task = progress.add_task("", total=100)
                for i in range(100):
                    progress.update(task, advance=1)
        """
        progress = Progress(
            SpinnerColumn(style=self.COLORS['cyan']),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(
                complete_style=self.COLORS['green'],
                finished_style=self.COLORS['cyan'],
                pulse_style=self.COLORS['blue']
            ),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        
        with progress:
            yield progress
    
    @contextmanager
    def spinner(self, message: str = "Loading..."):
        """
        Context manager for a spinner.
        
        Usage:
            with console.spinner("Fetching data..."):
                # do work
                time.sleep(2)
        """
        with self.console.status(
            f"[{self.COLORS['cyan']}]{message}[/{self.COLORS['cyan']}]",
            spinner="dots"
        ):
            yield
    
    @contextmanager
    def shimmer(self, message: str = "Loading..."):
        """
        Context manager for a text shimmering effect.
        Creates a wave of colors through the text.
        
        Usage:
            with console.shimmer("Processing data..."):
                # do work
                time.sleep(2)
        """
        import threading
        import itertools
        
        # Flexoki color cycle for shimmer effect
        shimmer_colors = [
            self.COLORS['cyan'],
            self.COLORS['blue'],
            self.COLORS['purple'],
            self.COLORS['magenta'],
            self.COLORS['purple'],
            self.COLORS['blue'],
        ]
        
        stop_event = threading.Event()
        
        def animate():
            color_cycle = itertools.cycle(shimmer_colors)
            while not stop_event.is_set():
                color = next(color_cycle)
                # Create shimmering effect by cycling colors
                self.console.print(
                    f"\r[{color}]{message}[/{color}]",
                    end="",
                    markup=True
                )
                time.sleep(0.15)
        
        # Start animation thread
        import time as time_module
        thread = threading.Thread(target=animate, daemon=True)
        thread.start()
        
        try:
            yield
        finally:
            stop_event.set()
            thread.join(timeout=0.5)
            # Clear the line
            self.console.print("\r" + " " * (len(message) + 10) + "\r", end="")
    
    def clear(self):
        """Clear the console."""
        self.console.clear()
    
    def newline(self, count: int = 1):
        """Print newlines."""
        self.console.print("\n" * (count - 1))


# Example usage
if __name__ == "__main__":
    import time
    
    console = Console()
    
    # Basic messages
    console.success("Operation completed successfully!")
    console.info("This is an informational message")
    console.warning("This is a warning message")
    console.error("This is an error message")
    console.newline()
    
    # Different text styles
    console.print("This is [highlight]highlighted[/highlight] text")
    console.muted("This is muted text")
    console.faint("This is faint text")
    console.newline()
    
    # Markdown
    console.markdown("""
# Flexoki Console
This console uses the **Flexoki** color scheme for a warm, inky feel.

- Feature 1: Themed messages
- Feature 2: Progress bars
- Feature 3: Spinners
    """)
    console.newline()
    
    # Panel
    console.panel(
        "This is content inside a panel with a nice border",
        title="Panel Example",
        style="info"
    )
    console.newline()
    
    # Progress bar
    with console.progress("Processing items") as progress:
        task = progress.add_task("", total=50)
        for i in range(50):
            time.sleep(0.02)
            progress.update(task, advance=1)
    
    console.newline()
    
    # Spinner
    with console.spinner("Fetching data from API..."):
        time.sleep(2)
    
    console.success("All demonstrations complete!")

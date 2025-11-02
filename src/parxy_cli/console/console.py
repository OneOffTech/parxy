"""
Flexoki-themed Console class for Rich library
Uses the warm, inky Flexoki color scheme by Steph Ango
https://stephango.com/flexoki
"""

import os
import sys
from rich.console import Console as RichConsole
from rich.theme import Theme
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.style import Style
from contextlib import contextmanager

from parxy_core.models.config import ParxyConfig

# Flexoki color palette (dark theme - 400 series)
COLORS_DARK = {
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
    'black': '#100F0F',
    'white': '#FFFCF0',
    'red': '#D14D41',
    'orange': '#DA702C',
    'yellow': '#D0A215',
    'green': '#879A39',
    'cyan': '#3AA99F',
    'blue': '#4385BE',
    'purple': '#8B7EC8',
    'magenta': '#CE5D97',
}

# Flexoki color palette (light theme - 600 series)
COLORS_LIGHT = {
    # Base colors
    'bg': '#FFFCF0',
    'bg_2': '#F2F0E5',
    'ui': '#E6E4D9',
    'ui_2': '#DAD8CE',
    'ui_3': '#B7B5AC',
    'tx_3': '#6F6E69',
    'tx_2': '#403E3C',
    'tx': '#100F0F',
    # Accent colors (600 series for light theme)
    'black': '#100F0F',
    'white': '#FFFCF0',
    'red': '#AF3029',
    'orange': '#BC5215',
    'yellow': '#AD8301',
    'green': '#66800B',
    'cyan': '#24837B',
    'blue': '#205EA6',
    'purple': '#5E409D',
    'magenta': '#A02F6F',
}


class Console:
    """
    A themed console wrapper using the Flexoki color scheme.
    Provides methods for styled output, progress bars, and spinners.
    Automatically detects terminal background and uses appropriate theme.
    """

    @staticmethod
    def detect_terminal_background(config: ParxyConfig = None):
        """
        Detect if the terminal has a light or dark background.
        Returns 'dark' or 'light'.

        Detection methods:
        1. Check ParxyConfig theme setting
        2. Check COLORFGBG environment variable
        3. Check TERM_PROGRAM for known terminals
        4. Default to 'dark' if uncertain

        Args:
            config: Optional ParxyConfig instance. If provided and theme is set, uses that value.
        """
        # Method 1: Check ParxyConfig theme setting (highest priority)
        if config is not None and config.theme is not None:
            return config.theme

        # Method 2: Check COLORFGBG environment variable
        # Format is typically "foreground;background" where background color:
        # 0-6 or 8 = dark background, 7 or 15 = light background
        colorfgbg = os.environ.get('COLORFGBG', '')
        if colorfgbg:
            parts = colorfgbg.split(';')
            if len(parts) >= 2:
                try:
                    bg_color = int(parts[-1])
                    # Background colors 0-6, 8 are dark; 7, 15 are light
                    if bg_color in (7, 15):
                        return 'light'
                    elif bg_color in (0, 1, 2, 3, 4, 5, 6, 8):
                        return 'dark'
                except ValueError:
                    pass

        # Method 3: Check for Windows Terminal light theme
        if sys.platform == 'win32':
            wt_profile = os.environ.get('WT_PROFILE_ID', '')
            # Windows Terminal doesn't expose theme directly, but we can check registry
            # For now, we'll default based on common settings
            pass

        # Method 4: Check TERM_PROGRAM for known defaults
        term_program = os.environ.get('TERM_PROGRAM', '').lower()
        if term_program in ('apple_terminal', 'iterm.app'):
            # These often default to light themes
            # But we can't be certain, so we won't make assumptions
            pass

        # Default to dark theme (most terminal defaults)
        return 'dark'

    def __init__(self, theme_mode=None, config: ParxyConfig = None):
        """
        Initialize the console with Flexoki theme.

        Args:
            theme_mode: Optional theme mode ('light' or 'dark').
                       If None, auto-detects based on config or terminal background.
            config: Optional ParxyConfig instance for loading theme from configuration.
        """
        # Load config if not provided
        if config is None:
            config = ParxyConfig()

        # Detect or use specified theme
        if theme_mode is None:
            theme_mode = self.detect_terminal_background(config)

        # Select appropriate color palette
        self.theme_mode = theme_mode
        self.COLORS = COLORS_LIGHT if theme_mode == 'light' else COLORS_DARK

        # Build theme with selected colors
        # Extend https://github.com/Textualize/rich/blob/master/rich/default_styles.py
        self.theme = Theme(
            {
                # Base text styles
                'default': f'{self.COLORS["tx"]}',
                'muted': f'{self.COLORS["tx_2"]}',
                'faint': f'{self.COLORS["tx_3"]}',
                'black': f'{self.COLORS["black"]}',
                'red': f'{self.COLORS["red"]}',
                'orange': f'{self.COLORS["orange"]}',
                'yellow': f'{self.COLORS["yellow"]}',
                'green': f'{self.COLORS["green"]}',
                'cyan': f'{self.COLORS["cyan"]}',
                'blue': f'{self.COLORS["blue"]}',
                'purple': f'{self.COLORS["purple"]}',
                'magenta': f'{self.COLORS["magenta"]}',
                'white': f'{self.COLORS["white"]}',
                # Message types
                'success': f'bold {self.COLORS["green"]}',
                'info': f'{self.COLORS["cyan"]}',
                'warning': f'bold {self.COLORS["orange"]}',
                'error': f'bold {self.COLORS["red"]}',
                # Semantic colors
                'highlight': f'bold {self.COLORS["yellow"]}',
                'link': f'underline {self.COLORS["blue"]}',
                'repr.number': Style(
                    color=self.COLORS['blue'], bold=True, italic=False
                ),
                'repr.number_complex': Style(
                    color=self.COLORS['blue'], bold=True, italic=False
                ),  # same
                # Progress/spinner colors
                'bar.complete': f'{self.COLORS["green"]}',
                'bar.finished': f'{self.COLORS["cyan"]}',
                'bar.pulse': f'{self.COLORS["blue"]}',
                'progress.description': f'{self.COLORS["tx_2"]}',
                'progress.percentage': f'{self.COLORS["tx_2"]}',
                'progress.filesize': f'{self.COLORS["tx_2"]}',
                'progress.filesize.total': f'{self.COLORS["tx_2"]}',
                'progress.download': f'{self.COLORS["tx_2"]}',
                'progress.elapsed': f'{self.COLORS["tx_2"]}',
                'progress.remaining': f'{self.COLORS["tx_2"]}',
                'progress.data.speed': f'{self.COLORS["tx_2"]}',
                'progress.spinner': f'{self.COLORS["tx_3"]}',
                'status.spinner': f'{self.COLORS["tx_3"]}',
                # Markdown styles
                'markdown.item.bullet': f'{self.COLORS["tx_3"]}',
                'markdown.item.number': f'{self.COLORS["tx_3"]}',
                'markdown.link': Style(color=self.COLORS['blue']),
                'markdown.link_url': Style(color=self.COLORS['blue'], underline=True),
                # ISO 8601 styles
                'iso8601.date': Style(bold=True),
                'iso8601.time': Style(bold=True),
                'iso8601.timezone': Style(bold=True),
            }
        )

        self.console = RichConsole(theme=self.theme)

    def print(self, *args, style=None, **kwargs):
        """Print with optional style."""
        self.console.print(*args, style=style, **kwargs)

    def success(self, message: str, prefix: str = '✓'):
        """Print a success message."""
        self.console.print(f'[success]{prefix}[/success] {message}')

    def info(self, message: str, prefix: str = 'ℹ'):
        """Print an info message."""
        self.console.print(f'[info]{prefix}[/info] {message}')

    def warning(self, message: str, prefix: str = '⚠'):
        """Print a warning message."""
        self.console.print(f'[warning]{prefix}[/warning] {message}')

    def error(self, message: str, prefix: str = '✗'):
        """Print an error message."""
        self.console.print(f'[error]{prefix}[/error] {message}')

    def muted(self, message: str):
        """Print muted text."""
        self.console.print(message, style='muted')

    def faint(self, message: str):
        """Print faint text."""
        self.console.print(message, style='faint')

    def highlight(self, message: str):
        """Print highlighted text."""
        self.console.print(message, style='highlight')

    def parxy(self):
        """Print Parxy and its tagline."""
        self.action(f'[bold]Parxy[/bold]', style='blue')
        self.print(f'[faint][italic]Every document matters.[/italic][/faint]')
        self.newline()

    def action(self, message: str, style: str = 'faint', space_before: bool = False):
        """Print a highlighted action."""
        if space_before:
            self.newline()
        self.print(f'[{style}]▣[/{style}] {message}')
        self.newline()

    def markdown(self, content: str):
        """Render markdown content."""
        md = Markdown(content, inline_code_theme='monokai')
        self.console.print(md)

    def panel(
        self,
        content: str,
        title: str = None,
        style: str = 'default',
        border_style: str = None,
    ):
        """Display content in a panel."""
        border_color = border_style or self.COLORS['ui_2']
        panel = Panel(content, title=title, border_style=border_color, style=style)
        self.console.print(panel)

    def rule(self, title: str = None, style: str = None):
        """Print a horizontal rule."""
        rule_style = style or self.COLORS['ui_2']
        self.console.rule(title, style=rule_style)

    @contextmanager
    def progress(self, description: str = 'Working...'):
        """
        Context manager for a progress bar.

        Usage:
            with console.progress("Processing files") as progress:
                task = progress.add_task("", total=100)
                for i in range(100):
                    progress.update(task, advance=1)
        """
        progress = Progress(
            # SpinnerColumn(style=self.COLORS['cyan']),
            TextColumn('[progress.description]{task.description}'),
            BarColumn(
                complete_style=self.COLORS['cyan'],
                finished_style=self.COLORS['green'],
                pulse_style=self.COLORS['blue'],
            ),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        with progress:
            yield progress

    @contextmanager
    def spinner(self, message: str = 'Loading...'):
        """
        Context manager for a spinner.

        Usage:
            with console.spinner("Fetching data..."):
                # do work
                time.sleep(2)
        """
        with self.console.status(
            f'[{self.COLORS["cyan"]}]{message}[/{self.COLORS["cyan"]}]',
            spinner='dots',
            spinner_style='bar.pulse',
        ):
            yield

    @contextmanager
    def shimmer(self, message: str = 'Loading...'):
        """
        Context manager for a text shimmering effect.
        Creates a wave of dimming through individual characters.

        Usage:
            with console.shimmer("Processing data..."):
                # do work
                time.sleep(2)
        """
        import threading
        import time as time_module

        # Use default text color and dimmed versions
        normal_color = self.COLORS['tx']
        dim_color = self.COLORS['tx_3']  # Dimmed/faded version
        mid_color = self.COLORS['tx_2']  # Slightly dimmed

        stop_event = threading.Event()

        # Create a Text object that will be updated
        display_text = Text()

        def create_shimmer_text(position):
            """Create a Text object with shimmer effect at given position."""
            text = Text()

            for i, char in enumerate(message):
                # Calculate distance from wave position
                distance = abs(i - position)

                if distance == 0:
                    # Center of wave - most dimmed
                    text.append(char, style=dim_color)
                elif distance == 1:
                    # Adjacent to center - slightly dimmed
                    text.append(char, style=mid_color)
                else:
                    # Normal brightness
                    text.append(char, style=normal_color)

            return text

        def animate(live):
            position = 0
            direction = 1  # 1 for forward, -1 for backward

            while not stop_event.is_set():
                # Update the live display with new shimmer position
                live.update(create_shimmer_text(position))

                # Move the wave position
                position += direction

                # Bounce the wave at the edges
                if position >= len(message) - 1:
                    direction = -1
                elif position <= 0:
                    direction = 1

                time_module.sleep(0.06)  # Animation speed

        # Create Live display
        with Live(
            create_shimmer_text(0), console=self.console, refresh_per_second=20
        ) as live:
            # Start animation thread
            thread = threading.Thread(target=animate, args=(live,), daemon=True)
            thread.start()

            try:
                yield
            finally:
                stop_event.set()
                thread.join(timeout=0.5)

    def clear(self):
        """Clear the console."""
        self.console.clear()

    def newline(self, count: int = 1):
        """Print newlines."""
        self.console.print('\n' * (count - 1))

    def get_theme_mode(self):
        """Get the current theme mode ('light' or 'dark')."""
        return self.theme_mode


# Example usage
if __name__ == '__main__':
    import time

    # Console automatically detects terminal background
    console = Console()

    console.print('# Parxy Cli Theme Demo')

    console.info(f'Using {console.get_theme_mode()} theme')
    console.newline()

    # Basic messages
    console.print('# Message Types')

    console.success('Operation completed successfully!')
    console.info('This is an informational message')
    console.warning('This is a warning message')
    console.error('This is an error message')
    console.newline()

    # Different text styles
    console.print('This is [highlight]highlighted[/highlight] text')
    console.print('This has [code]inline code[/code] text')
    console.muted('This is muted text')
    console.faint('This is faint text')
    console.newline()

    console.print(
        '[link="https://github.com/OneOffTech/parxy"]This is a clickable link[/link]'
    )
    console.newline()

    # Markdown
    console.markdown("""
# Flexoki Console

This console uses the **Flexoki** color scheme for a warm, inky feel.

- Feature 1: Auto-detects light/dark terminal background
- Feature 2: Themed messages (success, info, warning, error)
- Feature 3: Progress bars and spinners
- Feature 4: Shimmer effect for long operations
                     
## Formatting Examples
                     
**bold** and *italic* text
                     
[Markdown Link](https://github.com/OneOffTech/parxy)
                     
## Example Code

```python
def hello_world():
    print("Hello, Flexoki!")
```

```
def hello_world():
    print("Hello, Flexoki!")
```
                     
`Single line code block example`
                     

> Block quote
    """)
    console.newline()

    # Panel
    console.panel(
        'This is content inside a panel with a nice border',
        title='Panel Example',
        style='info',
    )
    console.newline()

    # Progress bar
    with console.progress('Processing items') as progress:
        task = progress.add_task('', total=50)
        for i in range(50):
            time.sleep(0.02)
            progress.update(task, advance=1)

    console.newline()

    # Spinner
    with console.spinner('Fetching data from API...'):
        time.sleep(2)

    console.newline()

    # Shimmer
    with console.shimmer('Fetching data from API...'):
        time.sleep(2)

    console.success('All demonstrations complete!')

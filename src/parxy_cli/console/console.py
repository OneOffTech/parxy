"""
Flexoki-themed Console class for Rich library
Uses the warm, inky Flexoki color scheme by Steph Ango
https://stephango.com/flexoki
"""

import os
import sys
from rich.console import Console as RichConsole
from rich.console import (
    ConsoleOptions,
    RenderResult,
    RenderableType,
    Console as RichConsole,
    Group,
)
from rich.theme import Theme
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.markdown import Markdown, Heading, TextElement, MarkdownContext
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.style import Style
from rich.padding import Padding
from contextlib import contextmanager
from typing import Optional
from markdown_it.token import Token

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


class MarkdownHeading(TextElement):
    """A heading."""

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> Heading:
        return cls(token)

    def on_enter(self, context: MarkdownContext) -> None:
        self.text = Text()
        context.enter_style(self.style_name)

    def __init__(self, token: Token) -> None:
        self.token = token
        self.style_name = f'markdown.{token.tag}'
        super().__init__()

    def __rich_console__(
        self, console: RichConsole, options: ConsoleOptions
    ) -> RenderResult:
        yield (
            Text('#' * int(self.token.tag[1]), style=self.style_name)
            .append(' ')
            .append_text(self.text)
        )


Markdown.elements['heading_open'] = MarkdownHeading


class Shimmer:
    """
    A renderable that creates a shimmering text effect.
    The shimmer is a wave that dims characters as it passes over them.

    This is a stateful renderable that advances its animation on each render,
    similar to Rich's Spinner class.
    """

    def __init__(
        self,
        text: str,
        normal_color: str,
        dim_color: str,
        mid_color: str,
        speed: float = 1.0,
    ):
        """
        Initialize the Shimmer renderable.

        Args:
            text: The text to shimmer
            normal_color: Color for normal (bright) characters
            dim_color: Color for the dimmest characters (center of wave)
            mid_color: Color for slightly dimmed characters (adjacent to center)
            speed: Animation speed multiplier (higher = faster)
        """
        self.text = text
        self.normal_color = normal_color
        self.dim_color = dim_color
        self.mid_color = mid_color
        self.speed = speed

        # Animation state
        self.position = 0
        self.direction = 1  # 1 for forward, -1 for backward
        self._frame_count = 0

    def __rich_console__(self, console, options):
        """Render the shimmer effect for the current frame."""
        # Advance animation based on speed
        # Update position every N frames based on speed
        frames_per_step = max(1, int(1.0 / self.speed))

        if self._frame_count % frames_per_step == 0:
            self.position += self.direction

            # Bounce at edges
            if self.position >= len(self.text) - 1:
                self.direction = -1
            elif self.position <= 0:
                self.direction = 1

        self._frame_count += 1

        # Create the shimmered text
        text = Text()
        for i, char in enumerate(self.text):
            distance = abs(i - self.position)

            if distance == 0:
                # Center of wave - most dimmed
                text.append(char, style=self.dim_color)
            elif distance == 1:
                # Adjacent to center - slightly dimmed
                text.append(char, style=self.mid_color)
            else:
                # Normal brightness
                text.append(char, style=self.normal_color)

        yield text

    def __rich_measure__(self, console, options):
        """Return the width of the shimmer text."""
        from rich.measure import Measurement

        text_length = len(self.text)
        return Measurement(text_length, text_length)


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
                ),
                # Progress/spinner colors
                'bar.complete': f'{self.COLORS["blue"]}',
                'bar.finished': f'{self.COLORS["blue"]}',
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
                'markdown.h1': Style(bold=True, color=self.COLORS['magenta']),
                'markdown.h2': Style(bold=True, color=self.COLORS['magenta']),
                'markdown.h3': Style(bold=True, color=self.COLORS['magenta']),
                'markdown.h4': Style(bold=True, color=self.COLORS['magenta']),
                'markdown.h5': Style(bold=True, color=self.COLORS['magenta']),
                'markdown.h6': Style(bold=True, color=self.COLORS['magenta']),
                'markdown.h7': Style(bold=True, color=self.COLORS['magenta']),
                'markdown.item.bullet': f'{self.COLORS["tx_3"]}',
                'markdown.item.number': f'{self.COLORS["tx_3"]}',
                'markdown.link': Style(color=self.COLORS['blue']),
                'markdown.link_url': Style(color=self.COLORS['blue'], underline=True),
                'markdown.hr': Style(color=self.COLORS['ui_2']),
                'markdown.block_quote': Style(
                    color=self.COLORS['tx_2'],
                    bgcolor=self.COLORS['ui'],
                    bold=False,
                ),
                # The blockquote bar on the left
                'markdown.blockquote.border': Style(
                    color=self.COLORS['cyan'], bold=True
                ),
                'markdown.code_block': Style(
                    bgcolor=self.COLORS['ui'], color=self.COLORS['tx']
                ),
                'code': Style(bgcolor=self.COLORS['ui'], color=self.COLORS['tx']),
                'markdown.code': Style(
                    bgcolor=self.COLORS['ui'], color=self.COLORS['tx']
                ),
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

    def _icon_and_text(
        self,
        message: str,
        icon: str = '✓',
        icon_style: str = 'default',
        padding: int = 1,
    ):
        from rich.table import Table

        grid = Table.grid(padding=(0, padding), expand=False)
        grid.add_column(
            width=1,
        )
        grid.add_column()

        grid.add_row(Text(icon, style=icon_style), Text(message))

        return grid

    def success(self, message: str, prefix: str = '✓', panel: bool = False):
        """Print a success message."""
        # prefix_text = Text(prefix, style='success')
        # padded_prefix = Padding(prefix_text, (0, 1))
        formatted = self._icon_and_text(
            message=message, icon=prefix, icon_style='success'
        )
        self.print(formatted) if not panel else self.panel(
            formatted, border_style='success'
        )

    def info(self, message: str, prefix: str = 'ℹ', panel: bool = False):
        """Print an info message."""
        formatted = self._icon_and_text(message=message, icon=prefix, icon_style='info')
        self.print(formatted) if not panel else self.panel(
            formatted, border_style='info'
        )

    def warning(self, message: str, prefix: str = '⚠', panel: bool = False):
        """Print a warning message."""
        formatted = self._icon_and_text(
            message=message, icon=prefix, icon_style='warning'
        )
        self.print(formatted) if not panel else self.panel(
            formatted, border_style='warning'
        )

    def error(self, message: str, prefix: str = '✗', panel: bool = False):
        """Print an error message."""
        formatted = self._icon_and_text(
            message=message, icon=prefix, icon_style='error'
        )
        self.print(formatted) if not panel else self.panel(
            formatted, border_style='error'
        )

    def muted(self, message: str):
        """Print muted text."""
        self.print(message, style='muted')

    def faint(self, message: str):
        """Print faint text."""
        self.print(message, style='faint')

    def highlight(self, message: str):
        """Print highlighted text."""
        self.print(message, style='highlight')

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

    def markdown(self, content: str, code_theme: str = 'monokai'):
        """
        Render markdown content with Flexoki theme styling.

        Args:
            content: Markdown content to render
            code_theme: Syntax highlighting theme for code blocks (default: 'monokai')
        """
        md = Markdown(
            content,
            code_theme=code_theme,
            hyperlinks=True,
            inline_code_lexer=None,
            inline_code_theme=code_theme,
        )
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
        panel = Panel(
            content,
            title=title,
            border_style=border_color,
            title_align='left',
            style=style,
        )
        self.console.print(panel)

    def quote(self, content: str, expand: bool = False):
        """
        Display a blockquote-style callout with cyan left border and background.
        Similar to markdown blockquotes but with enhanced styling.

        Args:
            content: The quote content (can be markdown)
            title: Optional title for the quote
        """
        from rich.table import Table

        # Create a table with a cyan left border and background
        table = Table.grid(padding=(0, 1), expand=expand)
        table.add_column(
            style=Style(
                color=self.COLORS['cyan'], bgcolor=self.COLORS['ui'], bold=True
            ),
            width=1,
        )
        table.add_column(
            style=Style(
                color=self.COLORS['tx_2'],
                bgcolor=self.COLORS['ui'],
            )
        )

        # Split content into lines for proper rendering
        lines = content.strip().split('\n')
        for line in lines:
            table.add_row('▌', line if line else ' ')

        # Add padding around the quote
        self.console.print(Padding(table, (1, 0)))

    def separator(self, title: str = None, style: str = None):
        """Print a horizontal separator."""
        rule_style = style or self.COLORS['ui_2']
        self.console.rule(title, style=rule_style, align='left')

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
            TextColumn('[progress.description]{task.description}'),
            BarColumn(),
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
    def shimmer(self, message: str = 'Loading...', speed: float = 1.0):
        """
        Context manager for a text shimmering effect.
        Creates a wave of dimming through individual characters.
        The shimmer is automatically cleared when the task completes.

        Args:
            message: The text to display with shimmer effect
            speed: Animation speed multiplier (default 1.0, higher = faster)

        Usage:
            with console.shimmer("Processing data..."):
                # do work
                time.sleep(2)
        """
        # Create Shimmer renderable with theme colors
        shimmer = Shimmer(
            text=message,
            normal_color=self.COLORS['tx'],
            dim_color=self.COLORS['tx_3'],
            mid_color=self.COLORS['tx_2'],
            speed=speed,
        )

        # Use Live display with transient=True to clear the shimmer when done
        with Live(
            shimmer,
            console=self.console,
            refresh_per_second=20,
            transient=True,
        ):
            yield

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

    console.markdown('# Parxy Cli Theme Demo')

    console.info(f'Using {console.get_theme_mode()} theme')
    console.newline()

    # Basic messages
    console.markdown('# Message Types')

    console.success('Operation completed successfully!')
    console.info('This is an informational message')
    console.warning('This is a warning message')
    console.error('This is an error message')
    console.newline()

    console.success('Operation completed successfully!', panel=True)
    console.info('This is an informational message', panel=True)
    console.warning('This is a warning message', panel=True)
    console.error('This is an error message', panel=True)
    console.newline()

    # Different text styles
    console.markdown('# Text styles')
    console.print('This is [highlight]highlighted[/highlight] text')
    console.print('This has [code]inline code[/code] text')
    console.muted('This is muted text')
    console.faint('This is faint text')
    console.print(
        '[bold]bold[/bold], [em]italic[/em] and [underline]underline[/underline]'
    )
    console.newline()

    console.markdown('# Link')
    console.print(
        '[link=https://github.com/OneOffTech/parxy]This is a clickable link[/link]'
    )
    console.newline()

    # Markdown
    console.markdown("""
# Parxy Console

This console uses the [**Flexoki**](https://stephango.com/flexoki) color scheme for a warm, inky feel.

1. Auto-detects light/dark terminal background
2. Themed messages (success, info, warning, error)
3. Progress bars and spinners
4. Shimmer effect for long operations

- a bullet
- in a bullet list

## All headings
                     
### heading 3
#### heading 4
##### heading 5
###### heading 6

   
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

    console.markdown('# Panels')
    # Panel
    console.panel(
        'This is content inside a panel with a nice border',
        title='Panel Example',
    )
    console.newline()

    console.panel(
        'Panel without a title',
    )
    console.newline()

    # Quote / Callout
    console.quote(
        'This is a beautifully styled blockquote with a cyan left border\n'
        'and a subtle background, perfect for highlighting important information.\n\n'
        'It supports multiple lines and looks great!'
    )
    console.newline()

    console.markdown('# Dividers')

    console.markdown('----')

    console.separator()

    console.separator('Separator with title')

    console.newline()
    console.markdown('# Progress')
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
        time.sleep(3)

    console.success('All demonstrations complete!')

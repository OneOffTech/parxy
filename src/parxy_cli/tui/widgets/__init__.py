"""Reusable widgets for the Parxy TUI."""

from parxy_cli.tui.widgets.file_tree_selector import FileTreeSelector, FilteredDirectoryTree
from parxy_cli.tui.widgets.parser_selector import ParserSelector
from parxy_cli.tui.widgets.results_viewer import (
    ResultsViewer,
    DiffViewer,
    SideBySideViewer,
    ParserResults,
)
from parxy_cli.tui.widgets.welcome_screen import WelcomeScreen
from parxy_cli.tui.widgets.welcome_container import WelcomeContainer
from parxy_cli.tui.widgets.footer import Footer
from parxy_cli.tui.widgets.logo import Logo

__all__ = [
    'FileTreeSelector',
    'FilteredDirectoryTree',
    'ParserSelector',
    'ResultsViewer',
    'DiffViewer',
    'SideBySideViewer',
    'ParserResults',
    'WelcomeScreen',
    'WelcomeContainer',
    'Footer',
    'Logo'
]

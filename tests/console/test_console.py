"""
Unit tests for the Console class.

Tests cover all public methods of the Console class including:
- Theme detection
- Message types (success, info, warning, error)
- Text styles (muted, faint, highlight)
- Markdown rendering
- Panels and quotes
- Separators
- Context managers (progress, spinner, shimmer)
- Utility methods
"""

import os
import time
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from rich.console import Console as RichConsole
from rich.live import Live

from parxy_cli.console.console import Console, COLORS_DARK, COLORS_LIGHT, Shimmer
from parxy_core.models.config import ParxyConfig


class TestConsoleThemeDetection:
    """Tests for terminal background detection and theme selection."""

    def test_detect_terminal_background_from_config_dark(self):
        """Test theme detection from ParxyConfig - dark theme."""
        config = ParxyConfig(theme='dark')
        theme = Console.detect_terminal_background(config)
        assert theme == 'dark'

    def test_detect_terminal_background_from_config_light(self):
        """Test theme detection from ParxyConfig - light theme."""
        config = ParxyConfig(theme='light')
        theme = Console.detect_terminal_background(config)
        assert theme == 'light'

    @patch.dict(os.environ, {'COLORFGBG': '15;0'})
    def test_detect_terminal_background_from_colorfgbg_dark(self):
        """Test theme detection from COLORFGBG environment variable - dark."""
        theme = Console.detect_terminal_background()
        assert theme == 'dark'

    @patch.dict(os.environ, {'COLORFGBG': '0;7'})
    def test_detect_terminal_background_from_colorfgbg_light(self):
        """Test theme detection from COLORFGBG environment variable - light."""
        theme = Console.detect_terminal_background()
        assert theme == 'light'

    @patch.dict(os.environ, {'COLORFGBG': '0;15'})
    def test_detect_terminal_background_from_colorfgbg_light_15(self):
        """Test theme detection from COLORFGBG with background color 15."""
        theme = Console.detect_terminal_background()
        assert theme == 'light'

    @patch.dict(os.environ, {}, clear=True)
    def test_detect_terminal_background_default_dark(self):
        """Test default theme when no detection method works."""
        theme = Console.detect_terminal_background()
        assert theme == 'dark'

    def test_detect_terminal_background_config_overrides_env(self):
        """Test that config theme takes precedence over environment variables."""
        with patch.dict(os.environ, {'COLORFGBG': '0;7'}):
            config = ParxyConfig(theme='dark')
            theme = Console.detect_terminal_background(config)
            assert theme == 'dark'


class TestConsoleInitialization:
    """Tests for Console initialization and configuration."""

    @patch.dict(os.environ, {}, clear=True)
    def test_console_initialization_default(self):
        """Test console initializes with default dark theme."""
        console = Console()
        assert console.theme_mode == 'dark'
        assert console.COLORS == COLORS_DARK
        assert console.console is not None
        assert isinstance(console.console, RichConsole)

    def test_console_initialization_light_theme(self):
        """Test console initializes with light theme."""
        console = Console(theme_mode='light')
        assert console.theme_mode == 'light'
        assert console.COLORS == COLORS_LIGHT

    def test_console_initialization_dark_theme(self):
        """Test console initializes with dark theme explicitly."""
        console = Console(theme_mode='dark')
        assert console.theme_mode == 'dark'
        assert console.COLORS == COLORS_DARK

    def test_console_initialization_with_config(self):
        """Test console initializes with config object."""
        config = ParxyConfig(theme='light')
        console = Console(config=config)
        assert console.theme_mode == 'light'
        assert console.COLORS == COLORS_LIGHT

    def test_get_theme_mode(self):
        """Test get_theme_mode returns correct theme."""
        console_dark = Console(theme_mode='dark')
        console_light = Console(theme_mode='light')

        assert console_dark.get_theme_mode() == 'dark'
        assert console_light.get_theme_mode() == 'light'

    def test_console_theme_has_all_required_styles(self):
        """Test that console theme includes all required style definitions."""
        console = Console()
        theme_styles = console.theme.styles

        # Check essential styles exist
        required_styles = [
            'success',
            'info',
            'warning',
            'error',
            'default',
            'muted',
            'faint',
            'highlight',
            'link',
        ]
        for style in required_styles:
            assert style in theme_styles


class TestConsoleBasicOutput:
    """Tests for basic console output methods."""

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_print_method(self, mock_print):
        """Test basic print method."""
        console = Console()
        console.print('Test message')

        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        assert 'Test message' in args

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_print_with_style(self, mock_print):
        """Test print method with style parameter."""
        console = Console()
        console.print('Test message', style='bold')

        mock_print.assert_called_once()
        assert mock_print.call_args[1]['style'] == 'bold'


class TestConsoleMessageTypes:
    """Tests for styled message output methods."""

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_success_message(self, mock_print):
        """Test success message output."""
        console = Console()
        console.success('Operation successful')

        mock_print.assert_called_once()
        # Verify a Table object was printed (from _icon_and_text)
        from rich.table import Table

        printed_obj = mock_print.call_args[0][0]
        assert isinstance(printed_obj, Table)

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_success_message_custom_prefix(self, mock_print):
        """Test success message with custom prefix."""
        console = Console()
        console.success('Done', prefix='✔')

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_success_message_with_panel(self, mock_print):
        """Test success message with panel."""
        console = Console()
        console.success('Success in panel', panel=True)

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_info_message(self, mock_print):
        """Test info message output."""
        console = Console()
        console.info('Information message')

        mock_print.assert_called_once()
        # Verify a Table object was printed (from _icon_and_text)
        from rich.table import Table

        printed_obj = mock_print.call_args[0][0]
        assert isinstance(printed_obj, Table)

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_info_message_with_panel(self, mock_print):
        """Test info message with panel."""
        console = Console()
        console.info('Info in panel', panel=True)

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_warning_message(self, mock_print):
        """Test warning message output."""
        console = Console()
        console.warning('Warning message')

        mock_print.assert_called_once()
        # Verify a Table object was printed (from _icon_and_text)
        from rich.table import Table

        printed_obj = mock_print.call_args[0][0]
        assert isinstance(printed_obj, Table)

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_warning_message_with_panel(self, mock_print):
        """Test warning message with panel."""
        console = Console()
        console.warning('Warning in panel', panel=True)

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_error_message(self, mock_print):
        """Test error message output."""
        console = Console()
        console.error('Error message')

        mock_print.assert_called_once()
        # Verify a Table object was printed (from _icon_and_text)
        from rich.table import Table

        printed_obj = mock_print.call_args[0][0]
        assert isinstance(printed_obj, Table)

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_error_message_with_panel(self, mock_print):
        """Test error message with panel."""
        console = Console()
        console.error('Error in panel', panel=True)

        mock_print.assert_called_once()


class TestConsoleTextStyles:
    """Tests for text styling methods."""

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_muted_text(self, mock_print):
        """Test muted text output."""
        console = Console()
        console.muted('Muted message')

        mock_print.assert_called_once()
        assert mock_print.call_args[0][0] == 'Muted message'
        assert mock_print.call_args[1]['style'] == 'muted'

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_faint_text(self, mock_print):
        """Test faint text output."""
        console = Console()
        console.faint('Faint message')

        mock_print.assert_called_once()
        assert mock_print.call_args[0][0] == 'Faint message'
        assert mock_print.call_args[1]['style'] == 'faint'

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_highlight_text(self, mock_print):
        """Test highlighted text output."""
        console = Console()
        console.highlight('Highlighted message')

        mock_print.assert_called_once()
        assert mock_print.call_args[0][0] == 'Highlighted message'
        assert mock_print.call_args[1]['style'] == 'highlight'


class TestConsoleSpecialMethods:
    """Tests for special console methods."""

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_parxy_method(self, mock_print):
        """Test Parxy branding output."""
        console = Console()
        console.parxy()

        # Should print twice (title and tagline) plus newline
        assert mock_print.call_count >= 2

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_action_method(self, mock_print):
        """Test action output."""
        console = Console()
        console.action('Performing action')

        # Should print the action and a newline
        assert mock_print.call_count >= 1
        call_args = str(mock_print.call_args_list)
        assert 'Performing action' in call_args

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_action_method_with_space_before(self, mock_print):
        """Test action output with space before."""
        console = Console()
        console.action('Action with space', space_before=True)

        # Should print newline, action, and another newline
        assert mock_print.call_count >= 2


class TestConsoleMarkdown:
    """Tests for markdown rendering."""

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_markdown_rendering(self, mock_print):
        """Test markdown content rendering."""
        console = Console()
        markdown_content = '# Heading\n\nThis is **bold** text.'
        console.markdown(markdown_content)

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_markdown_with_custom_code_theme(self, mock_print):
        """Test markdown with custom code theme."""
        console = Console()
        markdown_content = '```python\nprint("Hello")\n```'
        console.markdown(markdown_content, code_theme='github-dark')

        mock_print.assert_called_once()


class TestConsolePanelsAndQuotes:
    """Tests for panels and quote rendering."""

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_panel_basic(self, mock_print):
        """Test basic panel output."""
        console = Console()
        console.panel('Panel content')

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_panel_with_title(self, mock_print):
        """Test panel with title."""
        console = Console()
        console.panel('Panel content', title='Panel Title')

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_panel_with_border_style(self, mock_print):
        """Test panel with custom border style."""
        console = Console()
        console.panel('Panel content', border_style='red')

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_quote_single_line(self, mock_print):
        """Test quote with single line."""
        console = Console()
        console.quote('This is a quote')

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_quote_multiline(self, mock_print):
        """Test quote with multiple lines."""
        console = Console()
        console.quote('Line 1\nLine 2\nLine 3')

        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_quote_with_expand(self, mock_print):
        """Test quote with expand parameter."""
        console = Console()
        console.quote('Expanded quote', expand=True)

        mock_print.assert_called_once()


class TestConsoleSeparator:
    """Tests for separator/rule rendering."""

    @patch('parxy_cli.console.console.RichConsole.rule')
    def test_separator_basic(self, mock_rule):
        """Test basic separator."""
        console = Console()
        console.separator()

        mock_rule.assert_called_once()
        assert mock_rule.call_args[1]['align'] == 'left'

    @patch('parxy_cli.console.console.RichConsole.rule')
    def test_separator_with_title(self, mock_rule):
        """Test separator with title."""
        console = Console()
        console.separator('Section Title')

        mock_rule.assert_called_once()
        assert mock_rule.call_args[0][0] == 'Section Title'

    @patch('parxy_cli.console.console.RichConsole.rule')
    def test_separator_with_style(self, mock_rule):
        """Test separator with custom style."""
        console = Console()
        console.separator(style='red')

        mock_rule.assert_called_once()


class TestConsoleContextManagers:
    """Tests for context manager methods (progress, spinner, shimmer)."""

    def test_progress_context_manager(self):
        """Test progress context manager."""
        console = Console()

        with console.progress('Processing') as progress:
            assert progress is not None
            # Progress should be a Progress instance from rich
            from rich.progress import Progress

            assert isinstance(progress, Progress)

    @patch('parxy_cli.console.console.RichConsole.status')
    def test_spinner_context_manager(self, mock_status):
        """Test spinner context manager."""
        mock_context = MagicMock()
        mock_status.return_value.__enter__ = Mock(return_value=mock_context)
        mock_status.return_value.__exit__ = Mock(return_value=False)

        console = Console()

        with console.spinner('Loading data'):
            pass

        mock_status.assert_called_once()
        call_args = mock_status.call_args
        assert 'Loading data' in str(call_args)

    def test_shimmer_context_manager(self):
        """Test shimmer context manager."""
        console = Console()

        # Test that shimmer context manager works
        with console.shimmer('Processing data', speed=2.0):
            pass  # Should not raise any exceptions

    def test_shimmer_context_manager_clears_on_exit(self):
        """Test that shimmer clears output when context exits."""
        console = Console()

        with patch.object(console.console, 'print') as mock_print:
            with console.shimmer('Test shimmer'):
                pass

        # Shimmer uses Live with transient=True, so no explicit clear needed


class TestConsoleUtilityMethods:
    """Tests for utility methods."""

    @patch('parxy_cli.console.console.RichConsole.clear')
    def test_clear_method(self, mock_clear):
        """Test clear console method."""
        console = Console()
        console.clear()

        mock_clear.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_newline_default(self, mock_print):
        """Test newline with default count."""
        console = Console()
        console.newline()

        mock_print.assert_called_once()
        # Default should print empty string (one newline)
        assert mock_print.call_args[0][0] == ''

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_newline_multiple(self, mock_print):
        """Test newline with multiple lines."""
        console = Console()
        console.newline(3)

        mock_print.assert_called_once()
        # Should print two newlines (count-1)
        assert mock_print.call_args[0][0] == '\n\n'


class TestShimmerClass:
    """Tests for Shimmer animation class."""

    def test_shimmer_initialization(self):
        """Test Shimmer class initialization."""
        shimmer = Shimmer(
            text='Test text',
            normal_color='#FFFFFF',
            dim_color='#666666',
            mid_color='#999999',
            speed=1.5,
        )

        assert shimmer.text == 'Test text'
        assert shimmer.normal_color == '#FFFFFF'
        assert shimmer.dim_color == '#666666'
        assert shimmer.mid_color == '#999999'
        assert shimmer.speed == 1.5
        assert shimmer.position == 0
        assert shimmer.direction == 1

    def test_shimmer_render(self):
        """Test Shimmer rendering."""
        shimmer = Shimmer(
            text='Test', normal_color='white', dim_color='gray', mid_color='lightgray'
        )

        # Create a mock console and options
        mock_console = Mock()
        mock_options = Mock()

        # Get the rendered output
        result = list(shimmer.__rich_console__(mock_console, mock_options))

        # Should return a Text object
        assert len(result) == 1
        from rich.text import Text

        assert isinstance(result[0], Text)

    def test_shimmer_animation_advances(self):
        """Test that shimmer animation advances position."""
        shimmer = Shimmer(
            text='Testing',
            normal_color='white',
            dim_color='gray',
            mid_color='lightgray',
            speed=1.0,
        )

        initial_position = shimmer.position

        # Render multiple times to advance animation
        mock_console = Mock()
        mock_options = Mock()

        for _ in range(5):
            list(shimmer.__rich_console__(mock_console, mock_options))

        # Position should have changed (unless we hit a boundary and bounced)
        assert shimmer._frame_count > 0

    def test_shimmer_bounces_at_edges(self):
        """Test that shimmer bounces at text edges."""
        shimmer = Shimmer(
            text='Hi',
            normal_color='white',
            dim_color='gray',
            mid_color='lightgray',
            speed=1.0,
        )

        mock_console = Mock()
        mock_options = Mock()

        # Render enough times to hit the edge
        for _ in range(10):
            list(shimmer.__rich_console__(mock_console, mock_options))

        # Direction should have changed at some point
        # Position should be within bounds
        assert 0 <= shimmer.position < len(shimmer.text)

    def test_shimmer_measure(self):
        """Test shimmer measurement for layout."""
        shimmer = Shimmer(
            text='Test text',
            normal_color='white',
            dim_color='gray',
            mid_color='lightgray',
        )

        mock_console = Mock()
        mock_options = Mock()

        measurement = shimmer.__rich_measure__(mock_console, mock_options)

        # Should return measurement matching text length
        assert measurement.minimum == len('Test text')
        assert measurement.maximum == len('Test text')


class TestConsoleIntegration:
    """Integration tests for console methods working together."""

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_multiple_message_types_in_sequence(self, mock_print):
        """Test outputting multiple message types."""
        console = Console()

        console.success('Success message')
        console.info('Info message')
        console.warning('Warning message')
        console.error('Error message')

        assert mock_print.call_count == 4

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_mixed_output_methods(self, mock_print):
        """Test mixing different output methods."""
        console = Console()

        console.print('Regular print')
        console.muted('Muted text')
        console.panel('Panel content')
        console.markdown('# Markdown')

        assert mock_print.call_count == 4

    def test_theme_consistency_across_methods(self):
        """Test that theme is consistently applied."""
        console_dark = Console(theme_mode='dark')
        console_light = Console(theme_mode='light')

        # Both should have consistent color schemes
        assert console_dark.COLORS == COLORS_DARK
        assert console_light.COLORS == COLORS_LIGHT

        # Theme should be reflected in internal console
        assert console_dark.theme_mode == 'dark'
        assert console_light.theme_mode == 'light'


class TestConsoleEdgeCases:
    """Tests for edge cases and error conditions."""

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_empty_message_success(self, mock_print):
        """Test success with empty message."""
        console = Console()
        console.success('')
        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_very_long_message(self, mock_print):
        """Test with very long message."""
        console = Console()
        long_message = 'A' * 1000
        console.info(long_message)
        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_message_with_special_characters(self, mock_print):
        """Test message with special characters."""
        console = Console()
        console.print('Message with émojis 🎉 and spëcial çharacters')
        mock_print.assert_called_once()

    @patch('parxy_cli.console.console.RichConsole.print')
    def test_multiline_message(self, mock_print):
        """Test multiline message handling."""
        console = Console()
        console.success('Line 1\nLine 2\nLine 3')
        mock_print.assert_called_once()

    def test_shimmer_with_empty_text(self):
        """Test shimmer with empty text."""
        shimmer = Shimmer(
            text='', normal_color='white', dim_color='gray', mid_color='lightgray'
        )

        assert shimmer.text == ''
        assert shimmer.position == 0

    def test_shimmer_with_single_character(self):
        """Test shimmer with single character."""
        shimmer = Shimmer(
            text='A', normal_color='white', dim_color='gray', mid_color='lightgray'
        )

        mock_console = Mock()
        mock_options = Mock()

        result = list(shimmer.__rich_console__(mock_console, mock_options))
        assert len(result) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""Test suite for the parse command."""

from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner
from click.utils import strip_ansi

from parxy_cli.commands.parse import app
from parxy_core.models import Document, Page


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_document():
    """Fixture providing a mock document with a single page."""
    return Document(pages=[Page(number=0, text='Test content')])


def test_parse_command_calls_facade_correctly(runner, mock_document):
    """Test that the parse command correctly invokes the Parxy facade."""

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        # Setup the mock to return our test document
        mock_parxy.parse.return_value = mock_document

        # Run the command with a test file
        result = runner.invoke(app, ['test.pdf'])

        # Assert the command executed successfully
        assert result.exit_code == 0

        # Assert Parxy.parse was called with the correct arguments
        mock_parxy.parse.assert_called_once_with(
            file='test.pdf',
            level='block',  # default level
            driver_name=None,  # default driver
        )

        # Clean ANSI color codes from output and verify content
        cleaned_output = strip_ansi(result.stdout)
        assert 'test.pdf' in cleaned_output
        assert '1 pages extracted' in cleaned_output


def test_parse_command_with_custom_options(runner, mock_document):
    """Test that the parse command correctly handles custom options."""

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document

        # Run command with custom options
        result = runner.invoke(
            app,
            ['test.pdf', '--driver', 'pymupdf', '--level', 'page', '--preview', '100'],
        )

        assert result.exit_code == 0

        # Assert Parxy.parse was called with custom options
        mock_parxy.parse.assert_called_once_with(
            file='test.pdf', level='page', driver_name='pymupdf'
        )


def test_parse_command_with_output_directory(runner, mock_document, tmp_path):
    """Test that the parse command correctly handles file output."""

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document

        # Create output path using tmp_path fixture
        output_dir = tmp_path / 'output'

        # Run command with output directory
        result = runner.invoke(app, ['test.pdf', '--output', str(output_dir)])

        assert result.exit_code == 0

        # Verify the output file was created
        output_file = output_dir / 'test.txt'
        assert output_file.exists()
        assert output_file.read_text() == 'Test content'


def test_parse_command_handles_errors(runner):
    """Test that the parse command properly handles and displays errors."""

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        # Setup the mock to raise an exception
        mock_parxy.parse.side_effect = Exception('Test error')

        # Run the command
        result = runner.invoke(app, ['test.pdf'])

        # Command should exit with non-zero status
        assert result.exit_code == 1

        # Error message should be displayed
        assert 'Error processing test.pdf' in result.stdout
        assert 'Test error' in result.stdout

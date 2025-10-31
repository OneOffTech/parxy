"""Test suite for the markdown command."""

from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner
from click.utils import strip_ansi

from parxy_cli.commands.markdown import app
from parxy_core.models import Document, Page


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_document():
    """Fixture providing a mock document with markdown content."""
    return Document(pages=[Page(number=0, text='# Test heading\n\nTest content')])


def test_markdown_command_calls_facade_correctly(runner, mock_document):
    """Test that the markdown command correctly invokes the Parxy facade."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
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
        assert 'Processing documents...' in cleaned_output
        assert 'file: "test.pdf"' in cleaned_output
        assert 'pages: 1' in cleaned_output
        assert '# Test heading' in cleaned_output


def test_markdown_command_with_custom_options(runner, mock_document):
    """Test that the markdown command correctly handles custom options."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document

        # Run command with custom options
        result = runner.invoke(
            app, ['test.pdf', '--driver', 'pymupdf', '--level', 'page']
        )

        assert result.exit_code == 0

        # Assert Parxy.parse was called with custom options
        mock_parxy.parse.assert_called_once_with(
            file='test.pdf', level='page', driver_name='pymupdf'
        )


def test_markdown_command_with_output_directory(runner, mock_document, tmp_path):
    """Test that the markdown command correctly handles file output."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document

        # Create output path using tmp_path fixture
        output_dir = tmp_path / 'output'

        # Run command with output directory
        result = runner.invoke(app, ['test.pdf', '--output', str(output_dir)])

        assert result.exit_code == 0

        # Verify the output file was created
        output_file = output_dir / 'test.md'
        assert output_file.exists()
        # Verify file content contains markdown
        content = output_file.read_text()
        assert 'file: "test.pdf"' in content
        assert 'pages: 1' in content
        assert '# Test heading' in content


def test_markdown_command_with_combine_option(runner, mock_document, tmp_path):
    """Test that the markdown command correctly handles combining multiple files."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document

        # Create output path using tmp_path fixture
        output_dir = tmp_path / 'output'

        # Run command with combine option and multiple files
        result = runner.invoke(
            app, ['test1.pdf', 'test2.pdf', '--output', str(output_dir), '--combine']
        )

        assert result.exit_code == 0

        # Verify the combined output file was created
        output_file = output_dir / 'combined_output.md'
        assert output_file.exists()

        # Verify file contains both documents
        content = output_file.read_text()
        assert '# test1.pdf' in content
        assert '# test2.pdf' in content
        assert content.count('# Test heading') == 2  # One for each input file


def test_markdown_command_handles_errors(runner):
    """Test that the markdown command properly handles and displays errors."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        # Setup the mock to raise an exception
        mock_parxy.parse.side_effect = Exception('Test error')

        # Run the command
        result = runner.invoke(app, ['test.pdf'])

        # Clean ANSI codes and verify error message
        cleaned_output = strip_ansi(result.stdout)
        assert 'Processing documents...' in cleaned_output
        assert 'Error processing test.pdf' in cleaned_output
        assert 'Test error' in cleaned_output

        # Unlike parse command, markdown continues on individual file errors
        assert result.exit_code == 0

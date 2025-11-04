"""Test suite for the parse command."""

from unittest.mock import patch
import pytest
from typer.testing import CliRunner

from parxy_cli.commands.parse import app, collect_files, collect_files_with_depth
from parxy_core.models import Document, Page


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_document():
    """Fixture providing a mock document with a single page."""
    return Document(
        pages=[Page(number=1, width=612.0, height=792.0, text='Test content')]
    )


def test_parse_command_calls_facade_correctly(runner, mock_document, tmp_path):
    """Test that the parse command correctly invokes the Parxy facade."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        # Setup the mock to return our test document
        mock_parxy.parse.return_value = mock_document
        mock_parxy.default_driver.return_value = 'pymupdf'

        # Run the command with a test file
        result = runner.invoke(app, [str(test_file)])

        # Assert the command executed successfully
        assert result.exit_code == 0

        # Assert Parxy.parse was called with the correct arguments
        mock_parxy.parse.assert_called_once_with(
            file=str(test_file),
            level='page',  # default level
            driver_name='pymupdf',  # default driver
        )


def test_parse_command_with_custom_options(runner, mock_document, tmp_path):
    """Test that the parse command correctly handles custom options."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document

        # Run command with custom options
        result = runner.invoke(
            app,
            [
                str(test_file),
                '--driver',
                'llamaparse',
                '--level',
                'block',
                '--mode',
                'plain',
            ],
        )

        assert result.exit_code == 0

        # Assert Parxy.parse was called with custom options
        mock_parxy.parse.assert_called_once_with(
            file=str(test_file), level='block', driver_name='llamaparse'
        )


def test_parse_command_with_output_directory(runner, mock_document, tmp_path):
    """Test that the parse command correctly handles file output."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document
        mock_parxy.default_driver.return_value = 'pymupdf'

        # Create output path using tmp_path fixture
        output_dir = tmp_path / 'output'

        # Run command with output directory
        result = runner.invoke(app, [str(test_file), '--output', str(output_dir)])

        assert result.exit_code == 0

        # Verify the output file was created (default mode is JSON)
        output_file = output_dir / 'test.json'
        assert output_file.exists()


def test_parse_command_with_markdown_output(runner, mock_document, tmp_path):
    """Test that the parse command correctly handles markdown output."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document
        mock_parxy.default_driver.return_value = 'pymupdf'

        # Create output path using tmp_path fixture
        output_dir = tmp_path / 'output'

        # Run command with markdown mode
        result = runner.invoke(
            app, [str(test_file), '--output', str(output_dir), '--mode', 'markdown']
        )

        assert result.exit_code == 0

        # Verify the output file was created with .md extension
        output_file = output_dir / 'test.md'
        assert output_file.exists()


def test_parse_command_handles_errors(runner, tmp_path):
    """Test that the parse command properly handles and displays errors."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        # Setup the mock to raise an exception
        mock_parxy.parse.side_effect = Exception('Test error')
        mock_parxy.default_driver.return_value = 'pymupdf'

        # Run the command
        result = runner.invoke(app, [str(test_file)])

        # Command should not exit with zero status (there was an error)
        # The command shows a warning but continues
        assert 'error' in result.stdout.lower()


def test_parse_command_with_multiple_drivers(runner, mock_document, tmp_path):
    """Test that the parse command correctly handles multiple drivers."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document

        # Create output path
        output_dir = tmp_path / 'output'

        # Run command with multiple drivers
        result = runner.invoke(
            app,
            [
                str(test_file),
                '--output',
                str(output_dir),
                '--driver',
                'pymupdf',
                '--driver',
                'llamaparse',
            ],
        )

        assert result.exit_code == 0

        # Verify that files with driver suffixes were created
        assert (output_dir / 'test-pymupdf.json').exists()
        assert (output_dir / 'test-llamaparse.json').exists()

        # Assert Parxy.parse was called twice (once per driver)
        assert mock_parxy.parse.call_count == 2


def test_collect_files_non_recursive(tmp_path):
    """Test that collect_files only finds files in the given directory when not recursive."""

    # Create test structure
    (tmp_path / 'doc1.pdf').write_text('test')
    (tmp_path / 'subdir').mkdir()
    (tmp_path / 'subdir' / 'doc2.pdf').write_text('test')

    files = collect_files([str(tmp_path)], recursive=False)

    # Should only find doc1.pdf, not doc2.pdf in subdir
    assert len(files) == 1
    assert files[0].name == 'doc1.pdf'


def test_collect_files_recursive(tmp_path):
    """Test that collect_files finds files in subdirectories when recursive=True."""

    # Create test structure
    (tmp_path / 'doc1.pdf').write_text('test')
    (tmp_path / 'subdir').mkdir()
    (tmp_path / 'subdir' / 'doc2.pdf').write_text('test')

    files = collect_files([str(tmp_path)], recursive=True)

    # Should find both files
    assert len(files) == 2
    file_names = {f.name for f in files}
    assert file_names == {'doc1.pdf', 'doc2.pdf'}


def test_collect_files_with_max_depth(tmp_path):
    """Test that collect_files respects max_depth parameter."""

    # Create test structure with 3 levels
    (tmp_path / 'doc1.pdf').write_text('test')
    (tmp_path / 'level1').mkdir()
    (tmp_path / 'level1' / 'doc2.pdf').write_text('test')
    (tmp_path / 'level1' / 'level2').mkdir()
    (tmp_path / 'level1' / 'level2' / 'doc3.pdf').write_text('test')

    # Test with max_depth=1 (should find doc1 and doc2, but not doc3)
    files = collect_files([str(tmp_path)], recursive=True, max_depth=1)

    assert len(files) == 2
    file_names = {f.name for f in files}
    assert file_names == {'doc1.pdf', 'doc2.pdf'}


def test_collect_files_with_depth_helper(tmp_path):
    """Test the collect_files_with_depth helper function."""

    # Create test structure
    (tmp_path / 'doc1.pdf').write_text('test')
    (tmp_path / 'level1').mkdir()
    (tmp_path / 'level1' / 'doc2.pdf').write_text('test')
    (tmp_path / 'level1' / 'level2').mkdir()
    (tmp_path / 'level1' / 'level2' / 'doc3.pdf').write_text('test')

    # Test with max_depth=0 (only current directory)
    files = collect_files_with_depth(tmp_path, '*.pdf', max_depth=0)
    assert len(files) == 1
    assert files[0].name == 'doc1.pdf'

    # Test with max_depth=2 (should find all files)
    files = collect_files_with_depth(tmp_path, '*.pdf', max_depth=2)
    assert len(files) == 3
    file_names = {f.name for f in files}
    assert file_names == {'doc1.pdf', 'doc2.pdf', 'doc3.pdf'}


def test_collect_files_with_individual_files(tmp_path):
    """Test that collect_files handles individual file paths correctly."""

    # Create test files
    file1 = tmp_path / 'doc1.pdf'
    file2 = tmp_path / 'doc2.pdf'
    file1.write_text('test')
    file2.write_text('test')

    files = collect_files([str(file1), str(file2)])

    assert len(files) == 2
    file_names = {f.name for f in files}
    assert file_names == {'doc1.pdf', 'doc2.pdf'}


def test_collect_files_mixed_files_and_folders(tmp_path):
    """Test that collect_files handles a mix of files and folders."""

    # Create test structure
    file1 = tmp_path / 'doc1.pdf'
    file1.write_text('test')

    folder = tmp_path / 'subdir'
    folder.mkdir()
    (folder / 'doc2.pdf').write_text('test')

    files = collect_files([str(file1), str(folder)], recursive=False)

    # Should find both files
    assert len(files) == 2
    file_names = {f.name for f in files}
    assert file_names == {'doc1.pdf', 'doc2.pdf'}


def test_parse_command_with_show_flag(runner, mock_document, tmp_path):
    """Test that the --show flag displays content in console."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.parse.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document
        mock_parxy.default_driver.return_value = 'pymupdf'

        # Run command with --show flag
        result = runner.invoke(app, [str(test_file), '--mode', 'plain', '--show'])

        assert result.exit_code == 0
        # Output should be shown in the console (the content would be empty in this case)

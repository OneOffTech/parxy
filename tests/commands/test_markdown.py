"""Test suite for the markdown command."""

from pathlib import Path
from unittest.mock import patch
import pytest
from typer.testing import CliRunner
from click.utils import strip_ansi

from parxy_cli.commands.markdown import app
from parxy_core.models import Document, Page, BatchResult


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_document():
    """Fixture providing a mock document with markdown content."""
    return Document(pages=[Page(number=0, text='# Test heading\n\nTest content')])


@pytest.fixture
def pdf_file(tmp_path):
    """Fixture providing a real temporary PDF file."""
    pdf = tmp_path / 'test.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake content')
    return pdf


def test_markdown_command_saves_file_with_driver_prefix(
    runner, mock_document, pdf_file
):
    """Test that output file is named with driver prefix, saved next to source file."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.default_driver.return_value = 'pymupdf'
        mock_parxy.batch_iter.return_value = iter(
            [
                BatchResult(
                    file=str(pdf_file),
                    driver='pymupdf',
                    document=mock_document,
                    error=None,
                )
            ]
        )

        result = runner.invoke(app, [str(pdf_file)])

        assert result.exit_code == 0

        mock_parxy.batch_iter.assert_called_once_with(
            tasks=[str(pdf_file)],
            drivers=['pymupdf'],
            level='block',
            workers=None,
        )

        expected_output = pdf_file.parent / 'pymupdf-test.md'
        assert expected_output.exists()
        assert '# Test heading' in expected_output.read_text()


def test_markdown_command_with_output_directory(
    runner, mock_document, pdf_file, tmp_path
):
    """Test that files are saved in the specified output directory with driver prefix."""

    output_dir = tmp_path / 'output'

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.default_driver.return_value = 'pymupdf'
        mock_parxy.batch_iter.return_value = iter(
            [
                BatchResult(
                    file=str(pdf_file),
                    driver='pymupdf',
                    document=mock_document,
                    error=None,
                )
            ]
        )

        result = runner.invoke(app, [str(pdf_file), '--output', str(output_dir)])

        assert result.exit_code == 0

        expected_output = output_dir / 'pymupdf-test.md'
        assert expected_output.exists()
        assert '# Test heading' in expected_output.read_text()


def test_markdown_command_with_custom_level(runner, mock_document, pdf_file):
    """Test that the --level option is passed through to batch_iter."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.batch_iter.return_value = iter(
            [
                BatchResult(
                    file=str(pdf_file),
                    driver='llamaparse',
                    document=mock_document,
                    error=None,
                )
            ]
        )

        result = runner.invoke(
            app, [str(pdf_file), '--driver', 'llamaparse', '--level', 'page']
        )

        assert result.exit_code == 0

        mock_parxy.batch_iter.assert_called_once_with(
            tasks=[str(pdf_file)],
            drivers=['llamaparse'],
            level='page',
            workers=None,
        )


def test_markdown_command_with_multiple_drivers(
    runner, mock_document, pdf_file, tmp_path
):
    """Test that multiple drivers produce separate output files."""

    output_dir = tmp_path / 'output'

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.batch_iter.return_value = iter(
            [
                BatchResult(
                    file=str(pdf_file),
                    driver='pymupdf',
                    document=mock_document,
                    error=None,
                ),
                BatchResult(
                    file=str(pdf_file),
                    driver='llamaparse',
                    document=mock_document,
                    error=None,
                ),
            ]
        )

        result = runner.invoke(
            app,
            [
                str(pdf_file),
                '--driver',
                'pymupdf',
                '--driver',
                'llamaparse',
                '--output',
                str(output_dir),
            ],
        )

        assert result.exit_code == 0
        assert (output_dir / 'pymupdf-test.md').exists()
        assert (output_dir / 'llamaparse-test.md').exists()


def test_markdown_command_inline_outputs_to_stdout(runner, mock_document, pdf_file):
    """Test that --inline prints YAML-frontmattered markdown to stdout without saving a file."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.default_driver.return_value = 'pymupdf'
        mock_parxy.batch_iter.return_value = iter(
            [
                BatchResult(
                    file=str(pdf_file),
                    driver='pymupdf',
                    document=mock_document,
                    error=None,
                )
            ]
        )

        result = runner.invoke(app, [str(pdf_file), '--inline'])

        assert result.exit_code == 0

        cleaned = strip_ansi(result.stdout)
        assert '---' in cleaned
        assert 'file:' in cleaned
        assert 'pages: 1' in cleaned
        assert '# Test heading' in cleaned

        # No output file should be written
        assert not (pdf_file.parent / 'pymupdf-test.md').exists()


def test_markdown_command_inline_rejected_with_multiple_files(runner, tmp_path):
    """Test that --inline exits with an error when more than one file is provided."""

    pdf1 = tmp_path / 'a.pdf'
    pdf2 = tmp_path / 'b.pdf'
    pdf1.write_bytes(b'%PDF fake')
    pdf2.write_bytes(b'%PDF fake')

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.default_driver.return_value = 'pymupdf'
        mock_parxy.batch_iter.return_value = iter([])

        result = runner.invoke(app, [str(pdf1), str(pdf2), '--inline'])

        assert result.exit_code == 1
        assert '--inline' in strip_ansi(result.stdout)


def test_markdown_command_handles_errors(runner, pdf_file):
    """Test that per-file errors are reported and processing continues."""

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.default_driver.return_value = 'pymupdf'
        mock_parxy.batch_iter.return_value = iter(
            [
                BatchResult(
                    file=str(pdf_file),
                    driver='pymupdf',
                    document=None,
                    error='Parse failed',
                )
            ]
        )

        result = runner.invoke(app, [str(pdf_file)])

        cleaned = strip_ansi(result.stdout)
        assert 'Parse failed' in cleaned


def test_markdown_command_stop_on_failure(runner, mock_document, tmp_path):
    """Test that --stop-on-failure exits immediately on first error."""

    pdf1 = tmp_path / 'a.pdf'
    pdf2 = tmp_path / 'b.pdf'
    pdf1.write_bytes(b'%PDF fake')
    pdf2.write_bytes(b'%PDF fake')

    with patch('parxy_cli.commands.markdown.Parxy') as mock_parxy:
        mock_parxy.default_driver.return_value = 'pymupdf'
        mock_parxy.batch_iter.return_value = iter(
            [
                BatchResult(
                    file=str(pdf1),
                    driver='pymupdf',
                    document=None,
                    error='Parse failed',
                ),
                BatchResult(
                    file=str(pdf2),
                    driver='pymupdf',
                    document=mock_document,
                    error=None,
                ),
            ]
        )

        result = runner.invoke(app, [str(pdf1), str(pdf2), '--stop-on-failure'])

        assert result.exit_code == 1
        assert 'stopping due to error' in strip_ansi(result.stdout).lower()


def test_markdown_command_no_files_found(runner, tmp_path):
    """Test that the command exits with an error when no PDF files are found."""

    empty_dir = tmp_path / 'empty'
    empty_dir.mkdir()

    with patch('parxy_cli.commands.markdown.Parxy'):
        result = runner.invoke(app, [str(empty_dir)])

        assert result.exit_code == 1

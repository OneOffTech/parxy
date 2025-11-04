"""Test suite for the preview command."""

from unittest.mock import patch
import pytest
from typer.testing import CliRunner
from click.utils import strip_ansi

from parxy_cli.commands.preview import (
    app,
    extract_toc,
    format_metadata,
    render_viewer_mode,
)
from parxy_core.models import Document, Page, Metadata, TextBlock, BoundingBox


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_document_simple():
    """Fixture providing a simple mock document with one page."""
    return Document(
        pages=[Page(number=1, width=612.0, height=792.0, text='Test content')]
    )


@pytest.fixture
def mock_document_with_metadata():
    """Fixture providing a mock document with metadata."""
    metadata = Metadata(
        title='Test Document',
        author='Test Author',
        subject='Test Subject',
        keywords='test, document',
        creator='Test Creator',
        producer='Test Producer',
        created_at='2024-01-01T00:00:00',
        updated_at='2024-01-02T00:00:00',
    )
    return Document(
        pages=[Page(number=1, width=612.0, height=792.0, text='Test content')],
        metadata=metadata,
    )


@pytest.fixture
def mock_document_with_headings():
    """Fixture providing a mock document with headings for TOC."""
    heading_block = TextBlock(
        type='text',
        text='Chapter 1: Introduction',
        category='heading',
        level=1,
        page=1,
        bbox=BoundingBox(x0=0, y0=0, x1=100, y1=20),
    )

    text_block = TextBlock(
        type='text',
        text='This is some content.',
        category='text',
        page=1,
        bbox=BoundingBox(x0=0, y0=25, x1=100, y1=40),
    )

    page = Page(
        number=1,
        width=612.0,
        height=792.0,
        text='Chapter 1: Introduction\nThis is some content.',
        blocks=[heading_block, text_block],
    )

    return Document(pages=[page])


def test_preview_command_calls_facade_correctly(runner, mock_document_simple, tmp_path):
    """Test that the preview command correctly invokes the Parxy facade."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.preview.Parxy') as mock_parxy:
        # Setup the mock to return our test document
        mock_parxy.parse.return_value = mock_document_simple

        # Run the command with a test file
        result = runner.invoke(app, [str(test_file)])

        # Assert the command executed successfully
        assert result.exit_code == 0

        # Assert Parxy.parse was called with the correct arguments
        mock_parxy.parse.assert_called_once_with(
            file=str(test_file),
            level='block',  # default level
            driver_name=None,  # default driver
        )


def test_preview_command_with_custom_driver(runner, mock_document_simple, tmp_path):
    """Test that the preview command correctly handles custom driver."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.preview.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document_simple

        # Run command with custom driver
        result = runner.invoke(app, [str(test_file), '--driver', 'llamaparse'])

        assert result.exit_code == 0

        # Assert Parxy.parse was called with custom driver
        mock_parxy.parse.assert_called_once_with(
            file=str(test_file), level='block', driver_name='llamaparse'
        )


def test_preview_command_with_custom_level(runner, mock_document_simple, tmp_path):
    """Test that the preview command correctly handles custom extraction level."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.preview.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document_simple

        # Run command with custom level
        result = runner.invoke(app, [str(test_file), '--level', 'page'])

        assert result.exit_code == 0

        # Assert Parxy.parse was called with custom level
        mock_parxy.parse.assert_called_once_with(
            file=str(test_file), level='page', driver_name=None
        )


def test_extract_toc_with_headings(mock_document_with_headings):
    """Test that extract_toc correctly extracts headings from document."""

    toc = extract_toc(mock_document_with_headings)

    assert len(toc) == 1
    assert toc[0]['text'] == 'Chapter 1: Introduction'
    assert toc[0]['level'] == 1
    assert toc[0]['page'] == 1


def test_extract_toc_without_headings(mock_document_simple):
    """Test that extract_toc returns empty list when no headings found."""

    toc = extract_toc(mock_document_simple)

    assert len(toc) == 0


def test_format_metadata_with_full_metadata(mock_document_with_metadata):
    """Test that format_metadata correctly formats all metadata fields."""

    formatted = format_metadata(mock_document_with_metadata.metadata, 1)

    assert 'Title:' in formatted
    assert 'Test Document' in formatted
    assert 'Author:' in formatted
    assert 'Test Author' in formatted
    assert 'Subject:' in formatted
    assert 'Keywords:' in formatted
    assert 'Creator:' in formatted
    assert 'Producer:' in formatted
    assert 'Created:' in formatted
    assert 'Updated:' in formatted
    assert 'Pages:[/bold] 1' in formatted  # Includes Rich markup


def test_format_metadata_with_no_metadata():
    """Test that format_metadata handles None metadata gracefully."""

    formatted = format_metadata(None, 5)

    assert 'Pages:[/bold] 5' in formatted  # Includes Rich markup
    # Should not crash, and should still show page count


def test_format_metadata_with_empty_metadata():
    """Test that format_metadata handles empty metadata object."""

    metadata = Metadata()
    formatted = format_metadata(metadata, 3)

    # Should show page count even with empty metadata
    assert 'Pages:[/bold] 3' in formatted  # Includes Rich markup


def test_render_viewer_mode_creates_layout(mock_document_with_metadata):
    """Test that render_viewer_mode creates a proper Layout object."""

    layout = render_viewer_mode(mock_document_with_metadata)

    # Verify we get a Layout object back
    from rich.layout import Layout

    assert isinstance(layout, Layout)

    # Verify the layout was created successfully (basic check)
    # The layout should have nested children
    assert layout is not None


def test_preview_command_handles_parsing_errors(runner, tmp_path):
    """Test that the preview command properly handles parsing errors."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.preview.Parxy') as mock_parxy:
        # Setup the mock to raise an exception
        mock_parxy.parse.side_effect = Exception('Test parsing error')

        # Run the command
        result = runner.invoke(app, [str(test_file)])

        # Command should exit with error
        assert result.exit_code != 0
        assert isinstance(result.exception, Exception)


def test_preview_command_output_contains_content(
    runner, mock_document_with_metadata, tmp_path
):
    """Test that preview command output includes document content."""

    # Create a test PDF file
    test_file = tmp_path / 'test.pdf'
    test_file.write_text('dummy pdf content')

    with patch('parxy_cli.commands.preview.Parxy') as mock_parxy:
        mock_parxy.parse.return_value = mock_document_with_metadata

        # Run command
        result = runner.invoke(app, [str(test_file)])

        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)
        assert 'Test content' in cleaned_output


def test_extract_toc_with_multiple_heading_levels():
    """Test that extract_toc handles multiple heading levels correctly."""

    heading1 = TextBlock(
        type='text',
        text='Chapter 1',
        category='heading',
        level=1,
        page=1,
        bbox=BoundingBox(x0=0, y0=0, x1=100, y1=20),
    )

    heading2 = TextBlock(
        type='text',
        text='Section 1.1',
        category='heading',
        level=2,
        page=1,
        bbox=BoundingBox(x0=0, y0=25, x1=100, y1=40),
    )

    page = Page(
        number=1,
        width=612.0,
        height=792.0,
        text='Chapter 1\nSection 1.1',
        blocks=[heading1, heading2],
    )

    doc = Document(pages=[page])

    toc = extract_toc(doc)

    assert len(toc) == 2
    assert toc[0]['text'] == 'Chapter 1'
    assert toc[0]['level'] == 1
    assert toc[1]['text'] == 'Section 1.1'
    assert toc[1]['level'] == 2


def test_extract_toc_with_title_category():
    """Test that extract_toc includes blocks with 'title' category."""

    title_block = TextBlock(
        type='text',
        text='Document Title',
        category='title',
        level=1,
        page=1,
        bbox=BoundingBox(x0=0, y0=0, x1=100, y1=20),
    )

    page = Page(
        number=1,
        width=612.0,
        height=792.0,
        text='Document Title',
        blocks=[title_block],
    )

    doc = Document(pages=[page])

    toc = extract_toc(doc)

    assert len(toc) == 1
    assert toc[0]['text'] == 'Document Title'
    # The TOC dictionary only has text, level, and page keys
    assert 'text' in toc[0]
    assert 'level' in toc[0]
    assert 'page' in toc[0]

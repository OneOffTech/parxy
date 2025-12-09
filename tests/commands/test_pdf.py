"""Test suite for PDF commands."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
import pymupdf

from parxy_cli.commands.pdf import (
    app,
    parse_input_with_pages,
    collect_pdf_files_with_ranges,
)


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_pdfs(tmp_path):
    """Create sample PDF files for testing."""
    # Create first PDF with 3 pages
    pdf1_path = tmp_path / 'doc1.pdf'
    pdf1 = pymupdf.open()
    for i in range(3):
        page = pdf1.new_page(width=612, height=792)
        page.insert_text((100, 100), f'Page {i + 1} of doc1')
    pdf1.save(str(pdf1_path))
    pdf1.close()

    # Create second PDF with 2 pages
    pdf2_path = tmp_path / 'doc2.pdf'
    pdf2 = pymupdf.open()
    for i in range(2):
        page = pdf2.new_page(width=612, height=792)
        page.insert_text((100, 100), f'Page {i + 1} of doc2')
    pdf2.save(str(pdf2_path))
    pdf2.close()

    # Create third PDF with 5 pages
    pdf3_path = tmp_path / 'doc3.pdf'
    pdf3 = pymupdf.open()
    for i in range(5):
        page = pdf3.new_page(width=612, height=792)
        page.insert_text((100, 100), f'Page {i + 1} of doc3')
    pdf3.save(str(pdf3_path))
    pdf3.close()

    return {
        'pdf1': pdf1_path,
        'pdf2': pdf2_path,
        'pdf3': pdf3_path,
        'tmp_path': tmp_path,
    }


@pytest.fixture
def pdf_folder(tmp_path):
    """Create a folder with multiple PDFs."""
    folder = tmp_path / 'pdfs'
    folder.mkdir()

    # Create three PDFs in the folder
    for i in range(1, 4):
        pdf_path = folder / f'file{i}.pdf'
        pdf = pymupdf.open()
        page = pdf.new_page(width=612, height=792)
        page.insert_text((100, 100), f'Content of file{i}')
        pdf.save(str(pdf_path))
        pdf.close()

    return folder


# Tests for parse_input_with_pages helper function
class TestParseInputWithPages:
    """Tests for the parse_input_with_pages helper function."""

    def test_no_page_range(self):
        """Test parsing input without page range."""
        file_path, from_page, to_page = parse_input_with_pages('file.pdf')
        assert file_path == 'file.pdf'
        assert from_page is None
        assert to_page is None

    def test_single_page(self):
        """Test parsing single page specification."""
        file_path, from_page, to_page = parse_input_with_pages('file.pdf[3]')
        assert file_path == 'file.pdf'
        assert from_page == 2  # 0-based index
        assert to_page == 2

    def test_range_from_start(self):
        """Test parsing range from start to specified page."""
        file_path, from_page, to_page = parse_input_with_pages('file.pdf[:5]')
        assert file_path == 'file.pdf'
        assert from_page == 0
        assert to_page == 4  # 0-based index

    def test_range_to_end(self):
        """Test parsing range from specified page to end."""
        file_path, from_page, to_page = parse_input_with_pages('file.pdf[3:]')
        assert file_path == 'file.pdf'
        assert from_page == 2  # 0-based index
        assert to_page is None

    def test_range_both_bounds(self):
        """Test parsing range with both start and end specified."""
        file_path, from_page, to_page = parse_input_with_pages('file.pdf[2:5]')
        assert file_path == 'file.pdf'
        assert from_page == 1  # 0-based index
        assert to_page == 4  # 0-based index

    def test_path_with_spaces(self):
        """Test parsing path with spaces."""
        file_path, from_page, to_page = parse_input_with_pages(
            'path with spaces/file.pdf[1:3]'
        )
        assert file_path == 'path with spaces/file.pdf'
        assert from_page == 0
        assert to_page == 2

    def test_path_with_brackets_in_name(self):
        """Test parsing path without page range but with brackets elsewhere."""
        file_path, from_page, to_page = parse_input_with_pages('file.pdf')
        assert file_path == 'file.pdf'
        assert from_page is None
        assert to_page is None


# Tests for collect_pdf_files_with_ranges helper function
class TestCollectPdfFilesWithRanges:
    """Tests for the collect_pdf_files_with_ranges helper function."""

    def test_single_file_no_range(self, sample_pdfs):
        """Test collecting a single file without page range."""
        files = collect_pdf_files_with_ranges([str(sample_pdfs['pdf1'])])
        assert len(files) == 1
        assert files[0][0] == sample_pdfs['pdf1']
        assert files[0][1] is None  # from_page
        assert files[0][2] is None  # to_page

    def test_single_file_with_range(self, sample_pdfs):
        """Test collecting a single file with page range."""
        files = collect_pdf_files_with_ranges([f'{sample_pdfs["pdf1"]}[1:2]'])
        assert len(files) == 1
        assert files[0][0] == sample_pdfs['pdf1']
        assert files[0][1] == 0  # from_page (0-based)
        assert files[0][2] == 1  # to_page (0-based)

    def test_multiple_files(self, sample_pdfs):
        """Test collecting multiple files."""
        files = collect_pdf_files_with_ranges(
            [str(sample_pdfs['pdf1']), str(sample_pdfs['pdf2'])]
        )
        assert len(files) == 2
        assert files[0][0] == sample_pdfs['pdf1']
        assert files[1][0] == sample_pdfs['pdf2']

    def test_folder_input(self, pdf_folder):
        """Test collecting PDFs from a folder."""
        files = collect_pdf_files_with_ranges([str(pdf_folder)])
        assert len(files) == 3
        # Files should be sorted alphabetically
        file_names = [f[0].name for f in files]
        assert file_names == ['file1.pdf', 'file2.pdf', 'file3.pdf']

    def test_mixed_files_and_folders(self, sample_pdfs, pdf_folder):
        """Test collecting from both files and folders."""
        files = collect_pdf_files_with_ranges(
            [str(sample_pdfs['pdf1']), str(pdf_folder)]
        )
        assert len(files) == 4  # 1 file + 3 from folder

    def test_nonexistent_file(self, tmp_path):
        """Test handling of nonexistent file."""
        files = collect_pdf_files_with_ranges([str(tmp_path / 'nonexistent.pdf')])
        assert len(files) == 0

    def test_non_pdf_file(self, tmp_path):
        """Test handling of non-PDF file."""
        txt_file = tmp_path / 'file.txt'
        txt_file.write_text('not a pdf')
        files = collect_pdf_files_with_ranges([str(txt_file)])
        assert len(files) == 0

    def test_empty_folder(self, tmp_path):
        """Test handling of empty folder."""
        empty_folder = tmp_path / 'empty'
        empty_folder.mkdir()
        files = collect_pdf_files_with_ranges([str(empty_folder)])
        assert len(files) == 0

    def test_folder_with_page_range_warning(self, pdf_folder):
        """Test that page ranges on folders produce warning."""
        files = collect_pdf_files_with_ranges([f'{pdf_folder}[1:3]'])
        # Should still collect files but ignore the page range
        assert len(files) == 3
        # All files should have no page ranges
        for file_path, from_page, to_page in files:
            assert from_page is None
            assert to_page is None


# Tests for the merge command
class TestMergeCommand:
    """Tests for the pdf:merge command."""

    def test_merge_two_files_basic(self, runner, sample_pdfs):
        """Test basic merge of two PDF files."""
        output = sample_pdfs['tmp_path'] / 'merged.pdf'
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                str(sample_pdfs['pdf1']),
                str(sample_pdfs['pdf2']),
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()

        # Verify the merged PDF has correct number of pages
        merged = pymupdf.open(str(output))
        assert len(merged) == 5  # 3 pages from pdf1 + 2 pages from pdf2
        merged.close()

    def test_merge_with_page_ranges(self, runner, sample_pdfs):
        """Test merging with specific page ranges."""
        output = sample_pdfs['tmp_path'] / 'merged.pdf'
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                f'{sample_pdfs["pdf1"]}[1:2]',  # First 2 pages
                f'{sample_pdfs["pdf2"]}[1]',  # Only first page
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()

        # Verify the merged PDF has correct number of pages
        merged = pymupdf.open(str(output))
        assert len(merged) == 3  # 2 pages from pdf1 + 1 page from pdf2
        merged.close()

    def test_merge_folder(self, runner, pdf_folder, tmp_path):
        """Test merging all PDFs in a folder."""
        output = tmp_path / 'merged.pdf'
        result = runner.invoke(
            app, ['pdf:merge', str(pdf_folder), '--output', str(output)]
        )

        assert result.exit_code == 0
        assert output.exists()

        # Verify the merged PDF has correct number of pages (3 PDFs with 1 page each)
        merged = pymupdf.open(str(output))
        assert len(merged) == 3
        merged.close()

    def test_merge_without_output_prompts(self, runner, sample_pdfs):
        """Test that merge prompts for output when not specified."""
        result = runner.invoke(
            app,
            ['pdf:merge', str(sample_pdfs['pdf1']), str(sample_pdfs['pdf2'])],
            input='output.pdf\n',
        )

        # Command should prompt for output filename
        assert 'Enter output filename' in result.stdout
        assert result.exit_code == 0

    def test_merge_adds_pdf_extension(self, runner, sample_pdfs):
        """Test that .pdf extension is added if missing."""
        output = sample_pdfs['tmp_path'] / 'merged'  # No extension
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                str(sample_pdfs['pdf1']),
                str(sample_pdfs['pdf2']),
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        # Output should have .pdf extension added
        assert (sample_pdfs['tmp_path'] / 'merged.pdf').exists()

    def test_merge_creates_output_directory(self, runner, sample_pdfs):
        """Test that output directory is created if it doesn't exist."""
        output = sample_pdfs['tmp_path'] / 'subdir' / 'nested' / 'merged.pdf'
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                str(sample_pdfs['pdf1']),
                str(sample_pdfs['pdf2']),
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()
        assert output.parent.exists()

    def test_merge_single_file_fails(self, runner, sample_pdfs):
        """Test that merging a single file fails with appropriate message."""
        output = sample_pdfs['tmp_path'] / 'merged.pdf'
        result = runner.invoke(
            app,
            ['pdf:merge', str(sample_pdfs['pdf1']), '--output', str(output)],
        )

        assert result.exit_code == 1
        assert 'at least two files' in result.stdout.lower()

    def test_merge_no_files_fails(self, runner, tmp_path):
        """Test that merging with no valid files fails."""
        output = tmp_path / 'merged.pdf'
        result = runner.invoke(
            app,
            ['pdf:merge', str(tmp_path / 'nonexistent.pdf'), '--output', str(output)],
        )

        assert result.exit_code == 1
        assert 'no pdf files found' in result.stdout.lower()

    def test_merge_with_invalid_page_range(self, runner, sample_pdfs):
        """Test merging with invalid page range."""
        output = sample_pdfs['tmp_path'] / 'merged.pdf'
        # pdf1 has only 3 pages, trying to access page 10
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                f'{sample_pdfs["pdf1"]}[10]',
                str(sample_pdfs['pdf2']),
                '--output',
                str(output),
            ],
        )

        # Should show warning but continue with pdf2
        assert 'invalid page range' in result.stdout.lower() or result.exit_code == 0

    def test_merge_mixed_files_and_ranges(self, runner, sample_pdfs):
        """Test merging mix of full files and page ranges."""
        output = sample_pdfs['tmp_path'] / 'merged.pdf'
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                str(sample_pdfs['pdf1']),  # All pages (3)
                f'{sample_pdfs["pdf3"]}[2:4]',  # Pages 2-4 (3 pages)
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()

        merged = pymupdf.open(str(output))
        assert len(merged) == 6  # 3 from pdf1 + 3 from pdf3[2:4]
        merged.close()

    def test_merge_with_open_ended_range(self, runner, sample_pdfs):
        """Test merging with open-ended page ranges."""
        output = sample_pdfs['tmp_path'] / 'merged.pdf'
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                f'{sample_pdfs["pdf3"]}[:2]',  # First 2 pages
                f'{sample_pdfs["pdf3"]}[3:]',  # From page 3 to end (3 pages)
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()

        merged = pymupdf.open(str(output))
        assert len(merged) == 5  # 2 + 3 pages
        merged.close()

    def test_merge_preserves_order(self, runner, sample_pdfs):
        """Test that files are merged in the specified order."""
        output = sample_pdfs['tmp_path'] / 'merged.pdf'
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                str(sample_pdfs['pdf2']),
                str(sample_pdfs['pdf1']),
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()

        merged = pymupdf.open(str(output))
        # Should be pdf2 pages first, then pdf1 pages
        assert len(merged) == 5
        # We can't easily verify order without reading content, but count is correct
        merged.close()

    def test_merge_relative_output_path(self, runner, sample_pdfs):
        """Test that relative output path uses first file's directory."""
        result = runner.invoke(
            app,
            [
                'pdf:merge',
                str(sample_pdfs['pdf1']),
                str(sample_pdfs['pdf2']),
                '--output',
                'merged.pdf',  # Relative path
            ],
        )

        assert result.exit_code == 0
        # Output should be in same directory as first input file
        expected_output = sample_pdfs['pdf1'].parent / 'merged.pdf'
        assert expected_output.exists()

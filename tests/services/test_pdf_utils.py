"""Test suite for PDF utility functions."""

import pytest
from pathlib import Path

from parxy_cli.services.pdf_utils import (
    format_file_size,
    validate_pdf_file,
    is_binary_file,
    parse_input_with_pages,
    collect_pdf_files_with_ranges,
)


# Tests for format_file_size
class TestFormatFileSize:
    """Tests for the format_file_size function."""

    def test_format_file_size_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(100) == '100.0 B'

    def test_format_file_size_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == '1.0 KB'
        assert format_file_size(1536) == '1.5 KB'

    def test_format_file_size_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1048576) == '1.0 MB'
        assert format_file_size(2621440) == '2.5 MB'

    def test_format_file_size_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1073741824) == '1.0 GB'

    def test_format_file_size_zero(self):
        """Test formatting zero bytes."""
        assert format_file_size(0) == '0.0 B'


# Tests for validate_pdf_file
class TestValidatePdfFile:
    """Tests for the validate_pdf_file function."""

    def test_validate_pdf_file_success(self, tmp_path):
        """Test validating a valid PDF file."""
        pdf_file = tmp_path / 'test.pdf'
        pdf_file.touch()
        path = validate_pdf_file(str(pdf_file))
        assert path == pdf_file

    def test_validate_pdf_file_not_found(self, tmp_path):
        """Test validating a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            validate_pdf_file(str(tmp_path / 'nonexistent.pdf'))

    def test_validate_pdf_file_not_pdf(self, tmp_path):
        """Test validating a non-PDF file."""
        txt_file = tmp_path / 'file.txt'
        txt_file.write_text('not a pdf')
        with pytest.raises(ValueError):
            validate_pdf_file(str(txt_file))

    def test_validate_pdf_file_case_insensitive(self, tmp_path):
        """Test that .PDF extension (uppercase) is accepted."""
        pdf_file = tmp_path / 'test.PDF'
        pdf_file.touch()
        path = validate_pdf_file(str(pdf_file))
        assert path == pdf_file


# Tests for is_binary_file
class TestIsBinaryFile:
    """Tests for the is_binary_file function."""

    def test_is_binary_file_text(self):
        """Test detecting text content."""
        text_content = b'This is plain text content'
        assert not is_binary_file(text_content)

    def test_is_binary_file_binary(self):
        """Test detecting binary content."""
        binary_content = b'\x00\x01\x02\x03'
        assert is_binary_file(binary_content)

    def test_is_binary_file_utf8(self):
        """Test detecting UTF-8 encoded text."""
        utf8_content = 'UTF-8 text with special chars: café'.encode('utf-8')
        assert not is_binary_file(utf8_content)

    def test_is_binary_file_empty(self):
        """Test detecting empty content."""
        empty_content = b''
        assert not is_binary_file(empty_content)

    def test_is_binary_file_long_text(self):
        """Test detecting long text content."""
        long_text = ('a' * 10000).encode('utf-8')
        assert not is_binary_file(long_text)


# Tests for parse_input_with_pages
class TestParseInputWithPages:
    """Tests for the parse_input_with_pages function."""

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

    def test_path_without_brackets(self):
        """Test parsing path without brackets."""
        file_path, from_page, to_page = parse_input_with_pages('file.pdf')
        assert file_path == 'file.pdf'
        assert from_page is None
        assert to_page is None


# Tests for collect_pdf_files_with_ranges
class TestCollectPdfFilesWithRanges:
    """Tests for the collect_pdf_files_with_ranges function."""

    @pytest.fixture
    def sample_pdfs(self, tmp_path):
        """Create sample PDF files for testing."""
        pdf1 = tmp_path / 'doc1.pdf'
        pdf1.touch()
        pdf2 = tmp_path / 'doc2.pdf'
        pdf2.touch()
        pdf3 = tmp_path / 'doc3.pdf'
        pdf3.touch()
        return {'pdf1': pdf1, 'pdf2': pdf2, 'pdf3': pdf3, 'tmp_path': tmp_path}

    @pytest.fixture
    def pdf_folder(self, tmp_path):
        """Create a folder with multiple PDFs."""
        folder = tmp_path / 'pdfs'
        folder.mkdir()

        for i in range(1, 4):
            pdf_path = folder / f'file{i}.pdf'
            pdf_path.touch()

        return folder

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

    def test_folder_with_page_range_ignores_range(self, pdf_folder):
        """Test that page ranges on folders are ignored."""
        files = collect_pdf_files_with_ranges([f'{pdf_folder}[1:3]'])
        # Should still collect files but ignore the page range
        assert len(files) == 3
        # All files should have no page ranges
        for file_path, from_page, to_page in files:
            assert from_page is None
            assert to_page is None

"""Test suite for PDF service."""

import pytest
from pathlib import Path
import pymupdf

from parxy_cli.services.pdf_service import PdfService


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF without attachments."""
    pdf_path = tmp_path / 'test.pdf'
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 100), 'Test document')
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_pdf_with_attachments(tmp_path):
    """Create a sample PDF with attached files."""
    # Create the main PDF
    pdf_path = tmp_path / 'document.pdf'
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 100), 'Test document with attachments')

    # Create and embed files
    text_content = b'This is a text file with some notes.'
    csv_content = b'name,value\nitem1,100\nitem2,200'

    doc.embfile_add(
        name='notes.txt',
        buffer_=text_content,
        filename='notes.txt',
        desc='Text notes',
    )
    doc.embfile_add(
        name='data.csv',
        buffer_=csv_content,
        filename='data.csv',
        desc='Sales data',
    )

    doc.save(str(pdf_path))
    doc.close()

    return {'pdf': pdf_path, 'tmp_path': tmp_path}


@pytest.fixture
def sample_files(tmp_path):
    """Create sample files for attaching."""
    text_file = tmp_path / 'file1.txt'
    text_file.write_text('Sample text content')

    csv_file = tmp_path / 'file2.csv'
    csv_file.write_text('col1,col2\nval1,val2')

    return {'text': text_file, 'csv': csv_file}


@pytest.fixture
def multiple_pdfs(tmp_path):
    """Create multiple PDF files for testing merge."""
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

    return {'pdf1': pdf1_path, 'pdf2': pdf2_path, 'tmp_path': tmp_path}


# Tests for context manager
class TestContextManager:
    """Tests for the context manager functionality."""

    def test_context_manager_opens_and_closes(self, sample_pdf):
        """Test that context manager opens and closes the PDF."""
        with PdfService(sample_pdf) as pdf:
            assert pdf._doc is not None

    def test_operations_outside_context_manager_fail(self, sample_pdf):
        """Test that operations outside context manager raise RuntimeError."""
        pdf = PdfService(sample_pdf)
        with pytest.raises(RuntimeError):
            pdf.list_attachments()


# Tests for attachment operations
class TestAttachmentOperations:
    """Tests for attachment management operations."""

    def test_list_attachments_empty(self, sample_pdf):
        """Test listing attachments from PDF without attachments."""
        with PdfService(sample_pdf) as pdf:
            attachments = pdf.list_attachments()
            assert attachments == []

    def test_list_attachments_with_files(self, sample_pdf_with_attachments):
        """Test listing attachments from PDF with attachments."""
        with PdfService(sample_pdf_with_attachments['pdf']) as pdf:
            attachments = pdf.list_attachments()
            assert len(attachments) == 2
            assert 'notes.txt' in attachments
            assert 'data.csv' in attachments

    def test_get_attachment_info(self, sample_pdf_with_attachments):
        """Test getting attachment metadata."""
        with PdfService(sample_pdf_with_attachments['pdf']) as pdf:
            info = pdf.get_attachment_info('notes.txt')
            assert 'size' in info
            assert info['description'] == 'Text notes'

    def test_get_attachment_info_not_found(self, sample_pdf):
        """Test getting info for nonexistent attachment."""
        with PdfService(sample_pdf) as pdf:
            with pytest.raises(KeyError):
                pdf.get_attachment_info('nonexistent.txt')

    def test_add_attachment(self, sample_pdf, sample_files, tmp_path):
        """Test adding an attachment to PDF."""
        output = tmp_path / 'output.pdf'

        with PdfService(sample_pdf) as pdf:
            pdf.add_attachment(sample_files['text'])
            pdf.save(output)

        # Verify attachment was added
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert len(embeds) == 1
        assert 'file1.txt' in embeds
        doc.close()

    def test_add_attachment_with_custom_name(self, sample_pdf, sample_files, tmp_path):
        """Test adding attachment with custom name."""
        output = tmp_path / 'output.pdf'

        with PdfService(sample_pdf) as pdf:
            pdf.add_attachment(sample_files['text'], name='custom.txt')
            pdf.save(output)

        # Verify custom name
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert 'custom.txt' in embeds
        assert 'file1.txt' not in embeds
        doc.close()

    def test_add_attachment_with_description(self, sample_pdf, sample_files, tmp_path):
        """Test adding attachment with description."""
        output = tmp_path / 'output.pdf'

        with PdfService(sample_pdf) as pdf:
            pdf.add_attachment(sample_files['text'], desc='Custom description')
            pdf.save(output)

        # Verify description
        doc = pymupdf.open(str(output))
        info = doc.embfile_info('file1.txt')
        assert info['description'] == 'Custom description'
        doc.close()

    def test_add_attachment_file_not_found(self, sample_pdf, tmp_path):
        """Test adding nonexistent file."""
        with PdfService(sample_pdf) as pdf:
            with pytest.raises(FileNotFoundError):
                pdf.add_attachment(tmp_path / 'nonexistent.txt')

    def test_remove_attachment(self, sample_pdf_with_attachments, tmp_path):
        """Test removing an attachment."""
        output = tmp_path / 'output.pdf'

        with PdfService(sample_pdf_with_attachments['pdf']) as pdf:
            pdf.remove_attachment('notes.txt')
            pdf.save(output)

        # Verify attachment was removed
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert 'notes.txt' not in embeds
        assert 'data.csv' in embeds
        doc.close()

    def test_remove_attachment_not_found(self, sample_pdf):
        """Test removing nonexistent attachment."""
        with PdfService(sample_pdf) as pdf:
            with pytest.raises(KeyError):
                pdf.remove_attachment('nonexistent.txt')

    def test_extract_attachment(self, sample_pdf_with_attachments):
        """Test extracting attachment content."""
        with PdfService(sample_pdf_with_attachments['pdf']) as pdf:
            content = pdf.extract_attachment('notes.txt')
            assert b'text file with some notes' in content

    def test_extract_attachment_not_found(self, sample_pdf):
        """Test extracting nonexistent attachment."""
        with PdfService(sample_pdf) as pdf:
            with pytest.raises(KeyError):
                pdf.extract_attachment('nonexistent.txt')


# Tests for save operation
class TestSaveOperation:
    """Tests for saving PDFs."""

    def test_save_creates_output_directory(self, sample_pdf, tmp_path):
        """Test that save creates output directory if needed."""
        output = tmp_path / 'subdir' / 'nested' / 'output.pdf'

        with PdfService(sample_pdf) as pdf:
            pdf.save(output)

        assert output.exists()
        assert output.parent.exists()


# Tests for static operations
class TestMergePdfs:
    """Tests for the merge_pdfs static method."""

    def test_merge_two_files(self, multiple_pdfs):
        """Test merging two PDF files."""
        output = multiple_pdfs['tmp_path'] / 'merged.pdf'

        PdfService.merge_pdfs(
            [
                (multiple_pdfs['pdf1'], None, None),
                (multiple_pdfs['pdf2'], None, None),
            ],
            output,
        )

        assert output.exists()

        # Verify merged PDF has correct number of pages
        merged = pymupdf.open(str(output))
        assert len(merged) == 5  # 3 pages from pdf1 + 2 pages from pdf2
        merged.close()

    def test_merge_with_page_ranges(self, multiple_pdfs):
        """Test merging with specific page ranges."""
        output = multiple_pdfs['tmp_path'] / 'merged.pdf'

        PdfService.merge_pdfs(
            [
                (multiple_pdfs['pdf1'], 0, 1),  # First 2 pages (0-based)
                (multiple_pdfs['pdf2'], 0, 0),  # Only first page
            ],
            output,
        )

        assert output.exists()

        merged = pymupdf.open(str(output))
        assert len(merged) == 3  # 2 pages from pdf1 + 1 page from pdf2
        merged.close()

    def test_merge_file_not_found(self, tmp_path):
        """Test merging with nonexistent file."""
        output = tmp_path / 'merged.pdf'

        with pytest.raises(FileNotFoundError):
            PdfService.merge_pdfs(
                [(tmp_path / 'nonexistent.pdf', None, None)],
                output,
            )

    def test_merge_invalid_page_range(self, multiple_pdfs):
        """Test merging with invalid page range."""
        output = multiple_pdfs['tmp_path'] / 'merged.pdf'

        with pytest.raises(ValueError):
            PdfService.merge_pdfs(
                [(multiple_pdfs['pdf1'], 10, 20)],  # Invalid range
                output,
            )


class TestSplitPdf:
    """Tests for the split_pdf static method."""

    def test_split_into_individual_pages(self, multiple_pdfs):
        """Test splitting a PDF into individual pages."""
        output_dir = multiple_pdfs['tmp_path'] / 'split'

        output_files = PdfService.split_pdf(
            multiple_pdfs['pdf1'], output_dir, 'doc1'
        )

        assert len(output_files) == 3
        assert all(f.exists() for f in output_files)

        # Check filenames
        assert output_files[0].name == 'doc1_page_1.pdf'
        assert output_files[1].name == 'doc1_page_2.pdf'
        assert output_files[2].name == 'doc1_page_3.pdf'

        # Verify each file has exactly 1 page
        for output_file in output_files:
            pdf = pymupdf.open(str(output_file))
            assert len(pdf) == 1
            pdf.close()

    def test_split_file_not_found(self, tmp_path):
        """Test splitting nonexistent file."""
        output_dir = tmp_path / 'split'

        with pytest.raises(FileNotFoundError):
            PdfService.split_pdf(tmp_path / 'nonexistent.pdf', output_dir, 'prefix')

    def test_split_empty_pdf(self, tmp_path):
        """Test splitting empty PDF."""
        # Create a PDF and then manually create an empty one by bypassing pymupdf's save check
        # Since pymupdf doesn't allow saving empty PDFs, we'll test the ValueError from our service
        # by creating a PDF file with 1 page and then testing our service catches empty PDFs
        empty_pdf = tmp_path / 'empty.pdf'

        # Create a minimal PDF file that will report 0 pages
        # Since we can't create a truly empty PDF with pymupdf, we'll skip this test
        # or test it differently - our service will raise ValueError when pdf has 0 pages
        pytest.skip("PyMuPDF doesn't allow creating empty PDFs for testing")

    def test_split_creates_output_directory(self, multiple_pdfs):
        """Test that split creates output directory if needed."""
        output_dir = multiple_pdfs['tmp_path'] / 'nested' / 'split'

        output_files = PdfService.split_pdf(
            multiple_pdfs['pdf1'], output_dir, 'doc1'
        )

        assert output_dir.exists()
        assert len(output_files) == 3

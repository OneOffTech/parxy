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

        output_files = PdfService.split_pdf(multiple_pdfs['pdf1'], output_dir, 'doc1')

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

    def test_split_creates_output_directory(self, multiple_pdfs):
        """Test that split creates output directory if needed."""
        output_dir = multiple_pdfs['tmp_path'] / 'nested' / 'split'

        output_files = PdfService.split_pdf(multiple_pdfs['pdf1'], output_dir, 'doc1')

        assert output_dir.exists()
        assert len(output_files) == 3


class TestOptimizePdf:
    """Tests for the optimize_pdf static method."""

    @pytest.fixture
    def pdf_with_metadata_and_attachments(self, tmp_path):
        """Create a PDF with metadata, attachments for testing optimization."""
        pdf_path = tmp_path / 'heavy.pdf'
        doc = pymupdf.open()

        # Add pages with text
        for i in range(3):
            page = doc.new_page(width=612, height=792)
            page.insert_text((100, 100), f'Page {i + 1} content\n' * 20)

        # Add metadata
        doc.set_metadata({
            'author': 'Test Author',
            'title': 'Test Document',
            'subject': 'Testing PDF optimization',
            'keywords': 'test, optimization, metadata',
            'creator': 'Test Creator',
            'producer': 'PyMuPDF',
        })

        # Add attachments
        attachment_content = b'This is test attachment content ' * 100
        doc.embfile_add(
            name='attachment.txt',
            buffer_=attachment_content,
            filename='attachment.txt',
            desc='Test attachment',
        )

        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_optimize_with_all_defaults(self, tmp_path):
        """Test optimization with all default settings."""
        # Use existing fixture
        input_pdf = Path('tests/fixtures/pdf-with-attachment.pdf')
        output_pdf = tmp_path / 'optimized.pdf'

        result = PdfService.optimize_pdf(input_pdf, output_pdf)

        # Verify output exists
        assert output_pdf.exists()

        # Verify result structure
        assert 'original_size' in result
        assert 'optimized_size' in result
        assert 'reduction_bytes' in result
        assert 'reduction_percent' in result

        # Verify sizes are positive
        assert result['original_size'] > 0
        assert result['optimized_size'] > 0

        # For PDF with attachments and metadata, should see reduction
        assert result['reduction_bytes'] >= 0

    def test_optimize_reduces_file_size(self, pdf_with_metadata_and_attachments, tmp_path):
        """Test that optimization actually reduces file size."""
        output_pdf = tmp_path / 'optimized.pdf'

        result = PdfService.optimize_pdf(
            pdf_with_metadata_and_attachments,
            output_pdf,
            scrub_metadata=True,
            subset_fonts=True,
            compress_images=True,
        )

        # Should reduce size due to metadata and attachment removal
        assert result['optimized_size'] < result['original_size']
        assert result['reduction_bytes'] > 0
        assert result['reduction_percent'] > 0

    def test_optimize_without_scrubbing(self, pdf_with_metadata_and_attachments, tmp_path):
        """Test optimization without scrubbing metadata."""
        output_pdf = tmp_path / 'optimized.pdf'

        result = PdfService.optimize_pdf(
            pdf_with_metadata_and_attachments,
            output_pdf,
            scrub_metadata=False,
            subset_fonts=False,
            compress_images=False,
        )

        # Should still work, but may not reduce size much
        assert output_pdf.exists()
        assert result['optimized_size'] > 0

        # Verify metadata is preserved
        doc = pymupdf.open(str(output_pdf))
        metadata = doc.metadata
        assert metadata['author'] == 'Test Author'
        assert metadata['title'] == 'Test Document'

        # Verify attachments are preserved
        attachments = doc.embfile_names()
        assert 'attachment.txt' in attachments
        doc.close()

    def test_optimize_with_scrubbing_removes_metadata(
        self, pdf_with_metadata_and_attachments, tmp_path
    ):
        """Test that scrubbing removes metadata and attachments."""
        output_pdf = tmp_path / 'optimized.pdf'

        PdfService.optimize_pdf(
            pdf_with_metadata_and_attachments,
            output_pdf,
            scrub_metadata=True,
        )

        # Verify metadata is cleared
        doc = pymupdf.open(str(output_pdf))
        metadata = doc.metadata

        # Metadata should be empty or default values
        assert metadata['author'] == ''
        assert metadata['title'] == ''

        # Verify attachments are removed
        attachments = doc.embfile_names()
        assert len(attachments) == 0
        doc.close()

    def test_optimize_with_grayscale_conversion(self, tmp_path):
        """Test optimization with grayscale conversion."""
        input_pdf = Path('tests/fixtures/pdf-with-attachment.pdf')
        output_pdf = tmp_path / 'optimized.pdf'

        result = PdfService.optimize_pdf(
            input_pdf,
            output_pdf,
            compress_images=True,
            convert_to_grayscale=True,
        )

        assert output_pdf.exists()
        assert result['optimized_size'] > 0

    def test_optimize_with_custom_dpi_settings(self, tmp_path):
        """Test optimization with custom DPI settings."""
        input_pdf = Path('tests/fixtures/pdf-with-attachment.pdf')
        output_pdf = tmp_path / 'optimized.pdf'

        result = PdfService.optimize_pdf(
            input_pdf,
            output_pdf,
            compress_images=True,
            dpi_threshold=150,
            dpi_target=50,
            image_quality=50,
        )

        assert output_pdf.exists()
        assert result['optimized_size'] > 0

    def test_optimize_file_not_found(self, tmp_path):
        """Test optimization with nonexistent input file."""
        input_pdf = tmp_path / 'nonexistent.pdf'
        output_pdf = tmp_path / 'optimized.pdf'

        with pytest.raises(FileNotFoundError):
            PdfService.optimize_pdf(input_pdf, output_pdf)

    def test_optimize_invalid_dpi_threshold(self, tmp_path):
        """Test optimization with invalid DPI threshold."""
        input_pdf = Path('tests/fixtures/pdf-with-attachment.pdf')
        output_pdf = tmp_path / 'optimized.pdf'

        with pytest.raises(ValueError, match='DPI values must be positive'):
            PdfService.optimize_pdf(
                input_pdf,
                output_pdf,
                dpi_threshold=-1,
            )

    def test_optimize_invalid_dpi_target(self, tmp_path):
        """Test optimization with invalid DPI target."""
        input_pdf = Path('tests/fixtures/pdf-with-attachment.pdf')
        output_pdf = tmp_path / 'optimized.pdf'

        with pytest.raises(ValueError, match='DPI values must be positive'):
            PdfService.optimize_pdf(
                input_pdf,
                output_pdf,
                dpi_target=0,
            )

    def test_optimize_invalid_image_quality(self, tmp_path):
        """Test optimization with invalid image quality."""
        input_pdf = Path('tests/fixtures/pdf-with-attachment.pdf')
        output_pdf = tmp_path / 'optimized.pdf'

        with pytest.raises(ValueError, match='Image quality must be between 0 and 100'):
            PdfService.optimize_pdf(
                input_pdf,
                output_pdf,
                image_quality=150,
            )

    def test_optimize_creates_output_directory(self, tmp_path):
        """Test that optimize creates output directory if needed."""
        input_pdf = Path('tests/fixtures/pdf-with-attachment.pdf')
        output_pdf = tmp_path / 'nested' / 'subdir' / 'optimized.pdf'

        result = PdfService.optimize_pdf(input_pdf, output_pdf)

        assert output_pdf.exists()
        assert output_pdf.parent.exists()
        assert result['optimized_size'] > 0

    def test_optimize_calculates_reduction_correctly(
        self, pdf_with_metadata_and_attachments, tmp_path
    ):
        """Test that size reduction calculations are correct."""
        output_pdf = tmp_path / 'optimized.pdf'

        result = PdfService.optimize_pdf(
            pdf_with_metadata_and_attachments,
            output_pdf,
            scrub_metadata=True,
        )

        # Verify reduction calculation
        expected_reduction = result['original_size'] - result['optimized_size']
        assert result['reduction_bytes'] == expected_reduction

        expected_percent = (expected_reduction / result['original_size']) * 100
        assert abs(result['reduction_percent'] - expected_percent) < 0.01

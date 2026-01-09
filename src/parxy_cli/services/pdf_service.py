"""PDF manipulation service using PyMuPDF."""

from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import pymupdf


class PdfService:
    """
    Service for PDF manipulation operations using PyMuPDF.

    This class provides a high-level interface for PDF operations including
    attachment management, merging, and splitting. It uses context manager
    protocol for proper resource management.

    Example:
        with PdfService(pdf_path) as pdf:
            attachments = pdf.list_attachments()
            pdf.add_attachment(file_path, name="data.csv", desc="Sales data")
            pdf.save(output_path)
    """

    def __init__(self, pdf_path: Path):
        """
        Initialize PDF service with a PDF file path.

        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        self._doc = None

    def __enter__(self):
        """
        Open the PDF document when entering context manager.

        Returns:
            Self for method chaining
        """
        self._doc = pymupdf.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close the PDF document when exiting context manager.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if self._doc:
            self._doc.close()
        return False

    # ========================================================================
    # Attachment Operations
    # ========================================================================

    def list_attachments(self) -> List[str]:
        """
        List all attachment names in the PDF.

        Returns:
            List of attachment names

        Raises:
            RuntimeError: If called outside context manager
        """
        if not self._doc:
            raise RuntimeError('PdfService must be used within a context manager')
        return self._doc.embfile_names()

    def get_attachment_info(self, name: str) -> Dict[str, Any]:
        """
        Get metadata for a specific attachment.

        Args:
            name: Name of the attachment

        Returns:
            Dictionary containing attachment metadata (size, description, etc.)

        Raises:
            RuntimeError: If called outside context manager
            KeyError: If attachment not found
        """
        if not self._doc:
            raise RuntimeError('PdfService must be used within a context manager')

        attachments = self._doc.embfile_names()
        if name not in attachments:
            raise KeyError(f"Attachment '{name}' not found in PDF")

        return self._doc.embfile_info(name)

    def add_attachment(
        self,
        file_path: Path,
        name: Optional[str] = None,
        desc: str = '',
    ) -> None:
        """
        Add a file as an attachment to the PDF.

        Args:
            file_path: Path to the file to attach
            name: Custom name for the attachment (defaults to filename)
            desc: Description for the attachment

        Raises:
            RuntimeError: If called outside context manager
            FileNotFoundError: If file_path doesn't exist
        """
        if not self._doc:
            raise RuntimeError('PdfService must be used within a context manager')

        if not file_path.is_file():
            raise FileNotFoundError(f'File not found: {file_path}')

        # Use filename if no custom name provided
        embed_name = name if name else file_path.name

        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Add attachment
        self._doc.embfile_add(
            name=embed_name,
            buffer_=file_content,
            filename=file_path.name,
            desc=desc,
        )

    def remove_attachment(self, name: str) -> None:
        """
        Remove an attachment from the PDF.

        Args:
            name: Name of the attachment to remove

        Raises:
            RuntimeError: If called outside context manager
            KeyError: If attachment not found
        """
        if not self._doc:
            raise RuntimeError('PdfService must be used within a context manager')

        attachments = self._doc.embfile_names()
        if name not in attachments:
            raise KeyError(f"Attachment '{name}' not found in PDF")

        self._doc.embfile_del(name)

    def extract_attachment(self, name: str) -> bytes:
        """
        Extract attachment content from the PDF.

        Args:
            name: Name of the attachment to extract

        Returns:
            Raw bytes content of the attachment

        Raises:
            RuntimeError: If called outside context manager
            KeyError: If attachment not found
        """
        if not self._doc:
            raise RuntimeError('PdfService must be used within a context manager')

        attachments = self._doc.embfile_names()
        if name not in attachments:
            raise KeyError(f"Attachment '{name}' not found in PDF")

        return self._doc.embfile_get(name)

    def save(self, output_path: Path) -> None:
        """
        Save the PDF to a file.

        Args:
            output_path: Path where the PDF should be saved

        Raises:
            RuntimeError: If called outside context manager
        """
        if not self._doc:
            raise RuntimeError('PdfService must be used within a context manager')

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self._doc.save(str(output_path))

    # ========================================================================
    # Static Operations (Multiple PDFs)
    # ========================================================================

    @staticmethod
    def merge_pdfs(
        inputs: List[Tuple[Path, Optional[int], Optional[int]]],
        output: Path,
    ) -> None:
        """
        Merge multiple PDF files into a single PDF.

        Args:
            inputs: List of tuples (pdf_path, from_page, to_page) where
                   page numbers are 0-based. None means all pages or last page.
            output: Path where the merged PDF should be saved

        Raises:
            FileNotFoundError: If any input PDF doesn't exist
            ValueError: If page ranges are invalid
        """
        merged_pdf = pymupdf.open()

        try:
            for file_path, from_page, to_page in inputs:
                if not file_path.is_file():
                    raise FileNotFoundError(f'PDF file not found: {file_path}')

                pdf = pymupdf.open(file_path)

                # Determine page range to insert
                if from_page is None and to_page is None:
                    # Insert all pages
                    merged_pdf.insert_pdf(pdf)
                else:
                    # Insert specific page range
                    actual_from = from_page if from_page is not None else 0
                    actual_to = to_page if to_page is not None else (len(pdf) - 1)

                    # Validate page range
                    if actual_from < 0 or actual_from >= len(pdf):
                        pdf.close()
                        raise ValueError(
                            f'Invalid page range for {file_path.name}: page {actual_from + 1} does not exist'
                        )

                    if actual_to < 0 or actual_to >= len(pdf):
                        pdf.close()
                        raise ValueError(
                            f'Invalid page range for {file_path.name}: page {actual_to + 1} does not exist'
                        )

                    if actual_from > actual_to:
                        pdf.close()
                        raise ValueError(
                            f'Invalid page range for {file_path.name}: start page {actual_from + 1} > end page {actual_to + 1}'
                        )

                    merged_pdf.insert_pdf(pdf, from_page=actual_from, to_page=actual_to)

                pdf.close()

            # Ensure output directory exists
            output.parent.mkdir(parents=True, exist_ok=True)

            # Save the merged PDF
            merged_pdf.save(str(output))
        finally:
            merged_pdf.close()

    @staticmethod
    def split_pdf(input_path: Path, output_dir: Path, prefix: str) -> List[Path]:
        """
        Split a PDF file into individual pages.

        Args:
            input_path: Path to the PDF file to split
            output_dir: Directory where split PDFs should be saved
            prefix: Prefix for output filenames

        Returns:
            List of paths to the created PDF files

        Raises:
            FileNotFoundError: If input PDF doesn't exist
            ValueError: If PDF is empty or invalid
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        pdf = pymupdf.open(input_path)
        total_pages = pdf.page_count

        if total_pages == 0:
            pdf.close()
            raise ValueError('PDF file is empty (no pages)')

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        output_files = []

        try:
            # Split into individual pages
            for page_num in range(total_pages):
                output_file = output_dir / f'{prefix}_page_{page_num + 1}.pdf'
                output_pdf = pymupdf.open()
                output_pdf.insert_pdf(pdf, from_page=page_num, to_page=page_num)
                output_pdf.save(str(output_file))
                output_pdf.close()
                output_files.append(output_file)
        finally:
            pdf.close()

        return output_files

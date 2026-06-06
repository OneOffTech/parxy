"""PDF manipulation service using PyMuPDF."""

import re as _re
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
    def split_pdf(
        input_path: Path,
        output_dir: Path,
        prefix: str,
        from_page: Optional[int] = None,
        to_page: Optional[int] = None,
    ) -> List[Path]:
        """
        Split a PDF file into individual pages.

        Args:
            input_path: Path to the PDF file to split
            output_dir: Directory where split PDFs should be saved
            prefix: Prefix for output filenames
            from_page: First page to extract (0-based, inclusive). None means first page.
            to_page: Last page to extract (0-based, inclusive). None means last page.

        Returns:
            List of paths to the created PDF files

        Raises:
            FileNotFoundError: If input PDF doesn't exist
            ValueError: If PDF is empty or page range is invalid
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        pdf = pymupdf.open(input_path)
        total_pages = pdf.page_count

        if total_pages == 0:
            pdf.close()
            raise ValueError('PDF file is empty (no pages)')

        start = from_page if from_page is not None else 0
        end = to_page if to_page is not None else total_pages - 1

        if start < 0 or start >= total_pages:
            pdf.close()
            raise ValueError(
                f'Invalid page range: page {start + 1} does not exist (PDF has {total_pages} pages)'
            )

        if end < 0 or end >= total_pages:
            pdf.close()
            raise ValueError(
                f'Invalid page range: page {end + 1} does not exist (PDF has {total_pages} pages)'
            )

        if start > end:
            pdf.close()
            raise ValueError(
                f'Invalid page range: start page {start + 1} > end page {end + 1}'
            )

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        output_files = []

        try:
            for page_num in range(start, end + 1):
                output_file = output_dir / f'{prefix}_page_{page_num + 1}.pdf'
                output_pdf = pymupdf.open()
                output_pdf.insert_pdf(pdf, from_page=page_num, to_page=page_num)
                output_pdf.save(str(output_file))
                output_pdf.close()
                output_files.append(output_file)
        finally:
            pdf.close()

        return output_files

    @staticmethod
    def split_pdf_by_text(
        input_path: Path,
        output_dir: Path,
        prefix: str,
        patterns: List[str],
        mode: str = 'contains',
        ignore_case: bool = False,
        use_regex: bool = False,
        discard_before_first_match: bool = False,
    ) -> List[Tuple[Path, int, int]]:
        """
        Split a PDF into chunks whenever a page matches one or more text patterns.

        Each matching page becomes the first page of a new chunk. Pages before
        the first match form a preamble chunk unless discard_before_first_match
        is True.

        Args:
            input_path: Path to the PDF file to split
            output_dir: Directory where chunk PDFs should be saved
            prefix: Prefix for output filenames
            patterns: One or more text strings or regex patterns (OR logic)
            mode: Matching mode — 'contains' or 'starts-with'
            ignore_case: Case-insensitive matching
            use_regex: Treat patterns as regular expressions
            discard_before_first_match: Skip pages that appear before the first match

        Returns:
            List of (output_path, first_page_1based, last_page_1based) tuples

        Raises:
            FileNotFoundError: If input PDF doesn't exist
            ValueError: If patterns is empty, mode is invalid, PDF is empty,
                        or no matching pages are found
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        if not patterns:
            raise ValueError('At least one pattern must be provided')

        if mode not in ('contains', 'starts-with'):
            raise ValueError('mode must be "contains" or "starts-with"')

        flags = _re.IGNORECASE if ignore_case else 0
        compiled = [_re.compile(p, flags) for p in patterns] if use_regex else None

        def _matches(text: str) -> bool:
            check = text.lower() if ignore_case and not use_regex else text
            if use_regex:
                for pat in compiled:
                    if mode == 'starts-with':
                        if pat.match(text.lstrip()):
                            return True
                    else:
                        if pat.search(text):
                            return True
            else:
                for p in patterns:
                    check_p = p.lower() if ignore_case else p
                    if mode == 'starts-with':
                        if check.lstrip().startswith(check_p):
                            return True
                    else:
                        if check_p in check:
                            return True
            return False

        pdf = pymupdf.open(input_path)
        total_pages = pdf.page_count

        if total_pages == 0:
            pdf.close()
            raise ValueError('PDF file is empty (no pages)')

        # Find 0-based indices of pages that trigger a new chunk
        split_starts: List[int] = []
        for i in range(total_pages):
            page_text = pdf[i].get_text('text')
            if _matches(page_text):
                split_starts.append(i)

        if not split_starts:
            pdf.close()
            raise ValueError('No pages matched the given pattern(s)')

        # Build (start, end) 0-based inclusive ranges
        ranges: List[Tuple[int, int]] = []
        if not discard_before_first_match and split_starts[0] > 0:
            ranges.append((0, split_starts[0] - 1))
        for idx, start in enumerate(split_starts):
            end = (
                split_starts[idx + 1] - 1
                if idx + 1 < len(split_starts)
                else total_pages - 1
            )
            ranges.append((start, end))

        output_dir.mkdir(parents=True, exist_ok=True)
        output_files: List[Tuple[Path, int, int]] = []

        try:
            for chunk_idx, (start, end) in enumerate(ranges):
                page_label = (
                    f'p{start + 1}' if start == end else f'p{start + 1}-{end + 1}'
                )
                filename = f'{prefix}_part_{chunk_idx + 1:03d}_{page_label}.pdf'
                output_file = output_dir / filename
                output_pdf = pymupdf.open()
                output_pdf.insert_pdf(pdf, from_page=start, to_page=end)
                output_pdf.save(str(output_file))
                output_pdf.close()
                output_files.append((output_file, start + 1, end + 1))
        finally:
            pdf.close()

        return output_files

    @staticmethod
    def split_pdf_by_chunk(
        input_path: Path,
        output_dir: Path,
        prefix: str,
        chunk_size: int,
        from_page: Optional[int] = None,
        to_page: Optional[int] = None,
    ) -> List[Path]:
        """
        Split a PDF into chunks of N pages each.

        Args:
            input_path: Path to the PDF file to split
            output_dir: Directory where chunk PDFs should be saved
            prefix: Prefix for output filenames
            chunk_size: Number of pages per chunk
            from_page: First page to process (0-based, inclusive). None means first page.
            to_page: Last page to process (0-based, inclusive). None means last page.

        Returns:
            List of paths to the created PDF files

        Raises:
            FileNotFoundError: If input PDF doesn't exist
            ValueError: If PDF is empty, chunk_size < 1, or page range is invalid
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        if chunk_size < 1:
            raise ValueError('Chunk size must be at least 1')

        pdf = pymupdf.open(input_path)
        total_pages = pdf.page_count

        if total_pages == 0:
            pdf.close()
            raise ValueError('PDF file is empty (no pages)')

        start = from_page if from_page is not None else 0
        end = to_page if to_page is not None else total_pages - 1

        if start < 0 or start >= total_pages:
            pdf.close()
            raise ValueError(
                f'Invalid page range: page {start + 1} does not exist (PDF has {total_pages} pages)'
            )

        if end < 0 or end >= total_pages:
            pdf.close()
            raise ValueError(
                f'Invalid page range: page {end + 1} does not exist (PDF has {total_pages} pages)'
            )

        if start > end:
            pdf.close()
            raise ValueError(
                f'Invalid page range: start page {start + 1} > end page {end + 1}'
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        output_files = []

        try:
            chunk_start = start
            while chunk_start <= end:
                chunk_end = min(chunk_start + chunk_size - 1, end)
                if chunk_start == chunk_end:
                    filename = f'{prefix}_page_{chunk_start + 1}.pdf'
                else:
                    filename = f'{prefix}_pages_{chunk_start + 1}-{chunk_end + 1}.pdf'
                output_file = output_dir / filename
                output_pdf = pymupdf.open()
                output_pdf.insert_pdf(pdf, from_page=chunk_start, to_page=chunk_end)
                output_pdf.save(str(output_file))
                output_pdf.close()
                output_files.append(output_file)
                chunk_start = chunk_end + 1
        finally:
            pdf.close()

        return output_files

    @staticmethod
    def extract_pages(
        input_path: Path,
        output_path: Path,
        from_page: Optional[int] = None,
        to_page: Optional[int] = None,
    ) -> None:
        """
        Extract a page range from a PDF into a single output PDF.

        Args:
            input_path: Path to the source PDF file
            output_path: Path where the extracted PDF should be saved
            from_page: First page to extract (0-based, inclusive). None means first page.
            to_page: Last page to extract (0-based, inclusive). None means last page.

        Raises:
            FileNotFoundError: If input PDF doesn't exist
            ValueError: If PDF is empty or page range is invalid
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        pdf = pymupdf.open(input_path)
        total_pages = pdf.page_count

        if total_pages == 0:
            pdf.close()
            raise ValueError('PDF file is empty (no pages)')

        start = from_page if from_page is not None else 0
        end = to_page if to_page is not None else total_pages - 1

        if start < 0 or start >= total_pages:
            pdf.close()
            raise ValueError(
                f'Invalid page range: page {start + 1} does not exist (PDF has {total_pages} pages)'
            )

        if end < 0 or end >= total_pages:
            pdf.close()
            raise ValueError(
                f'Invalid page range: page {end + 1} does not exist (PDF has {total_pages} pages)'
            )

        if start > end:
            pdf.close()
            raise ValueError(
                f'Invalid page range: start page {start + 1} > end page {end + 1}'
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            output_pdf = pymupdf.open()
            output_pdf.insert_pdf(pdf, from_page=start, to_page=end)
            output_pdf.save(str(output_path))
            output_pdf.close()
        finally:
            pdf.close()

    # ========================================================================
    # Tagged PDF / Accessibility Operations
    # ========================================================================

    @staticmethod
    def _refs_in_value(value_type: str, value: str) -> List[int]:
        """
        Extract the indirect object numbers from a low-level key value.

        Handles both single references ('5 0 R') and arrays of references
        ('[5 0 R 6 0 R]'). Non-reference values (ints, names, MCIDs) yield
        an empty list.

        Args:
            value_type: The type reported by ``xref_get_key`` (e.g. 'xref', 'array')
            value: The raw value string reported by ``xref_get_key``

        Returns:
            List of object numbers referenced by the value, in order.
        """
        if value_type in ('xref', 'array'):
            return [int(m) for m in _re.findall(r'(\d+) 0 R', value)]
        return []

    @staticmethod
    def _string_key(doc, xref: int, key: str) -> Optional[str]:
        """Return a string-typed key value, or None if absent/not a string."""
        value_type, value = doc.xref_get_key(xref, key)
        return value if value_type == 'string' else None

    @staticmethod
    def is_tagged(input_path: Path) -> Dict[str, Any]:
        """
        Inspect a PDF to determine whether it is a tagged (accessible) PDF.

        A PDF is considered tagged when its catalog declares ``/MarkInfo``
        with ``/Marked true`` and references a ``/StructTreeRoot`` describing
        the logical structure tree.

        Args:
            input_path: Path to the PDF file

        Returns:
            Dictionary with detection details:
            - tagged: True when both marked and a structure tree are present
            - marked: Value of /MarkInfo /Marked
            - has_struct_tree: Whether /StructTreeRoot is present
            - lang: Document language (/Lang) if declared, else None
            - struct_element_count: Number of structure elements in the tree
            - page_count: Number of pages in the document

        Raises:
            FileNotFoundError: If input PDF doesn't exist
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        doc = pymupdf.open(input_path)
        try:
            cat = doc.pdf_catalog()

            _, marked_val = doc.xref_get_key(cat, 'MarkInfo/Marked')
            marked = marked_val == 'true'

            str_type, str_val = doc.xref_get_key(cat, 'StructTreeRoot')
            has_struct_tree = str_type == 'xref'

            lang = PdfService._string_key(doc, cat, 'Lang')

            struct_element_count = 0
            if has_struct_tree:
                root_xref = int(str_val.split()[0])
                k_type, k_val = doc.xref_get_key(root_xref, 'K')
                visited: set = set()
                stack = PdfService._refs_in_value(k_type, k_val)
                while stack:
                    xref = stack.pop()
                    if xref in visited:
                        continue
                    visited.add(xref)
                    s_type, _ = doc.xref_get_key(xref, 'S')
                    if s_type != 'name':
                        # Not a structure element (e.g. OBJR/MCR content ref)
                        continue
                    struct_element_count += 1
                    ck_type, ck_val = doc.xref_get_key(xref, 'K')
                    stack.extend(PdfService._refs_in_value(ck_type, ck_val))

            return {
                'tagged': marked and has_struct_tree,
                'marked': marked,
                'has_struct_tree': has_struct_tree,
                'lang': lang,
                'struct_element_count': struct_element_count,
                'page_count': doc.page_count,
            }
        finally:
            doc.close()

    @staticmethod
    def extract_tags(input_path: Path) -> Dict[str, Any]:
        """
        Extract the logical structure (tag) tree of a tagged PDF.

        Walks the ``/StructTreeRoot`` and returns the hierarchy of structure
        elements together with the page each element refers to (resolved from
        ``/Pg``, inherited from the nearest ancestor when absent).

        Each node is a dict with keys: ``type`` (structure type without the
        leading slash), ``page`` (1-based page number or None), ``alt``,
        ``actual_text``, ``title``, ``lang``, and ``children`` (list of nodes).

        Args:
            input_path: Path to the PDF file

        Returns:
            Dictionary with:
            - tagged: Whether a structure tree was found
            - roots: Top-level structure nodes
            - tag_counts: Mapping of structure type -> occurrence count
            - page_count: Number of pages in the document

        Raises:
            FileNotFoundError: If input PDF doesn't exist
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        doc = pymupdf.open(input_path)
        try:
            cat = doc.pdf_catalog()
            str_type, str_val = doc.xref_get_key(cat, 'StructTreeRoot')

            result: Dict[str, Any] = {
                'tagged': str_type == 'xref',
                'roots': [],
                'tag_counts': {},
                'page_count': doc.page_count,
            }

            if str_type != 'xref':
                return result

            # Map page object numbers to their 1-based page index
            page_map = {doc[i].xref: i + 1 for i in range(doc.page_count)}
            tag_counts: Dict[str, int] = {}
            visited: set = set()

            def _walk(xref: int, inherited_page: Optional[int]):
                if xref in visited:
                    return None
                visited.add(xref)

                s_type, s_val = doc.xref_get_key(xref, 'S')
                if s_type != 'name':
                    return None  # content reference, not a structure element
                structure_type = s_val.lstrip('/')

                pg_type, pg_val = doc.xref_get_key(xref, 'Pg')
                page = inherited_page
                if pg_type == 'xref':
                    page = page_map.get(int(pg_val.split()[0]), inherited_page)

                tag_counts[structure_type] = tag_counts.get(structure_type, 0) + 1

                children = []
                k_type, k_val = doc.xref_get_key(xref, 'K')
                for child_xref in PdfService._refs_in_value(k_type, k_val):
                    child = _walk(child_xref, page)
                    if child is not None:
                        children.append(child)

                return {
                    'type': structure_type,
                    'page': page,
                    'alt': PdfService._string_key(doc, xref, 'Alt'),
                    'actual_text': PdfService._string_key(doc, xref, 'ActualText'),
                    'title': PdfService._string_key(doc, xref, 'T'),
                    'lang': PdfService._string_key(doc, xref, 'Lang'),
                    'children': children,
                }

            root_xref = int(str_val.split()[0])
            rk_type, rk_val = doc.xref_get_key(root_xref, 'K')
            for child_xref in PdfService._refs_in_value(rk_type, rk_val):
                node = _walk(child_xref, None)
                if node is not None:
                    result['roots'].append(node)

            result['tag_counts'] = tag_counts
            return result
        finally:
            doc.close()

    @staticmethod
    def _struct_block_to_node(block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert a TEXT_COLLECT_STRUCTURE block into a structure node with text.

        Block types reported by PyMuPDF: 2 = structure element (with ``std``
        / ``raw`` type names and nested ``blocks``), 0 = text leaf (with
        ``lines``/``spans``), 1 = image. Text leaves become nodes with
        ``type`` None and their concatenated text; structure elements carry
        their type names and child nodes.
        """
        block_type = block.get('type')

        if block_type == 2:  # structure element
            node = {
                'type': block.get('raw'),
                'standard_type': block.get('std'),
                'text': None,
                'children': [],
            }
            for child in block.get('blocks', []):
                child_node = PdfService._struct_block_to_node(child)
                if child_node is not None:
                    node['children'].append(child_node)
            return node

        if block_type == 0:  # text leaf
            lines = []
            for line in block.get('lines', []):
                line_text = ''.join(
                    span.get('text', '') for span in line.get('spans', [])
                )
                if line_text:
                    lines.append(line_text)
            return {
                'type': None,
                'standard_type': None,
                'text': ' '.join(lines),
                'children': [],
            }

        if block_type == 1:  # image
            return {
                'type': 'Image',
                'standard_type': None,
                'text': None,
                'children': [],
            }

        return None

    @staticmethod
    def extract_tags_with_text(input_path: Path) -> Dict[str, Any]:
        """
        Extract the structure tree together with the text content of each tag.

        Unlike :meth:`extract_tags` (which walks the document-wide
        ``/StructTreeRoot`` and exposes accessibility attributes such as
        ``/Alt`` but no body text), this method reconstructs the structure
        **per page** using PyMuPDF's ``TEXT_COLLECT_STRUCTURE`` text
        extraction, so the visible text of ``P``, ``Strong``, ``Span`` and
        other elements is included.

        Each node is a dict with: ``type`` (raw structure type, or None for a
        bare text run), ``standard_type`` (the standardised type, e.g. a
        ``Strong`` maps to ``Span``), ``text`` (text content for leaves), and
        ``children``.

        Args:
            input_path: Path to the PDF file

        Returns:
            Dictionary with:
            - tagged: Whether the document declares a structure tree
            - page_count: Number of pages
            - pages: List of {'page': 1-based index, 'roots': [nodes]}

        Raises:
            FileNotFoundError: If input PDF doesn't exist
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        info = PdfService.is_tagged(input_path)

        doc = pymupdf.open(input_path)
        try:
            pages = []
            for i in range(doc.page_count):
                data = doc[i].get_text('dict', flags=pymupdf.TEXT_COLLECT_STRUCTURE)
                roots = []
                for block in data.get('blocks', []):
                    node = PdfService._struct_block_to_node(block)
                    if node is not None:
                        roots.append(node)
                pages.append({'page': i + 1, 'roots': roots})

            return {
                'tagged': info['tagged'],
                'page_count': doc.page_count,
                'pages': pages,
            }
        finally:
            doc.close()

    @staticmethod
    def create_tag_template(
        output_path: Path,
        pages: int = 1,
        lang: str = 'en-US',
        title: Optional[str] = None,
    ) -> None:
        """
        Create a minimal, empty tagged PDF skeleton for accessibility work.

        The generated document has the requested number of blank pages and a
        valid logical structure tree: ``/MarkInfo /Marked true``, a
        ``/StructTreeRoot`` containing a ``/Document`` element that groups one
        ``/P`` (paragraph) structure element per page.

        Args:
            output_path: Path where the template PDF should be saved
            pages: Number of blank pages to create (default: 1)
            lang: Document language tag set on the catalog (default: 'en-US')
            title: Optional document title stored in the PDF metadata

        Raises:
            ValueError: If pages < 1
        """
        if pages < 1:
            raise ValueError('A tagged template must have at least one page')

        doc = pymupdf.open()
        try:
            for _ in range(pages):
                doc.new_page()

            cat = doc.pdf_catalog()
            doc.xref_set_key(cat, 'MarkInfo/Marked', 'true')
            if lang:
                doc.xref_set_key(cat, 'Lang', f'({lang})')

            struct_root = doc.get_new_xref()
            document_elem = doc.get_new_xref()

            paragraph_refs = []
            for i in range(pages):
                para = doc.get_new_xref()
                page_xref = doc[i].xref
                doc.update_object(
                    para,
                    f'<< /Type /StructElem /S /P /P {document_elem} 0 R '
                    f'/Pg {page_xref} 0 R >>',
                )
                paragraph_refs.append(f'{para} 0 R')

            kids = ' '.join(paragraph_refs)
            doc.update_object(
                document_elem,
                f'<< /Type /StructElem /S /Document /P {struct_root} 0 R '
                f'/K [{kids}] >>',
            )
            doc.update_object(
                struct_root,
                f'<< /Type /StructTreeRoot /K [{document_elem} 0 R] >>',
            )
            doc.xref_set_key(cat, 'StructTreeRoot', f'{struct_root} 0 R')

            if title:
                doc.set_metadata({'title': title})

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path))
        finally:
            doc.close()

    @staticmethod
    def strip_to_tags(input_path: Path, output_path: Path) -> Dict[str, Any]:
        """
        Produce a copy of a tagged PDF that keeps the tag tree but no content.

        Every page's content stream is emptied so the visible text and images
        are removed, while the page objects and the ``/StructTreeRoot`` logical
        structure are preserved. Unused images and fonts are garbage-collected
        on save, yielding a lightweight artifact that still carries the
        accessibility structure for inspection and testing.

        Args:
            input_path: Path to the source tagged PDF
            output_path: Path where the stripped PDF should be saved

        Returns:
            Dictionary with:
            - tagged: Whether the source had a structure tree
            - struct_element_count: Structure elements preserved
            - page_count: Number of pages
            - original_size: Source file size in bytes
            - stripped_size: Output file size in bytes

        Raises:
            FileNotFoundError: If input PDF doesn't exist
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        info = PdfService.is_tagged(input_path)
        original_size = input_path.stat().st_size

        doc = pymupdf.open(input_path)
        try:
            for page in doc:
                for content_xref in page.get_contents():
                    doc.update_stream(content_xref, b' ')
                # Drop the page's resources (images, fonts, xobjects) so the
                # now-unused objects can be garbage-collected on save.
                doc.xref_set_key(page.xref, 'Resources', '<<>>')

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=4, deflate=True)
        finally:
            doc.close()

        return {
            'tagged': info['has_struct_tree'],
            'struct_element_count': info['struct_element_count'],
            'page_count': info['page_count'],
            'original_size': original_size,
            'stripped_size': output_path.stat().st_size,
        }

    # ========================================================================
    # Outline / Bookmarks Operations
    # ========================================================================

    @staticmethod
    def extract_outline(input_path: Path) -> Dict[str, Any]:
        """
        Extract the document outline (bookmarks / table of contents) of a PDF.

        Reads the PDF's ``/Outlines`` hierarchy via PyMuPDF's ``get_toc`` and
        returns both a flat list of entries (one per bookmark, with its nesting
        level) and a nested tree mirroring the bookmark hierarchy.

        Each tree node is a dict with: ``title`` (bookmark label), ``page``
        (1-based target page, or None when the destination has no page),
        ``level`` (1-based nesting depth), and ``children`` (list of nodes).
        Flat entries carry ``title``, ``page`` and ``level``.

        Args:
            input_path: Path to the PDF file

        Returns:
            Dictionary with:
            - has_outline: Whether the PDF defines any bookmarks
            - entries: Flat list of {'title', 'page', 'level'}
            - tree: Nested list of top-level outline nodes
            - entry_count: Total number of bookmarks
            - page_count: Number of pages in the document

        Raises:
            FileNotFoundError: If input PDF doesn't exist
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        doc = pymupdf.open(input_path)
        try:
            # toc rows are [level (1-based), title, page (1-based, -1 if none)]
            toc = doc.get_toc(simple=True)

            entries: List[Dict[str, Any]] = []
            tree: List[Dict[str, Any]] = []
            # Stack of (level, node) used to attach each entry to its parent
            stack: List[Tuple[int, Dict[str, Any]]] = []

            for level, title, page in toc:
                page_number = page if page and page > 0 else None
                entries.append(
                    {'title': title, 'page': page_number, 'level': level}
                )

                node = {
                    'title': title,
                    'page': page_number,
                    'level': level,
                    'children': [],
                }

                # Pop deeper-or-equal levels so the top of the stack is the parent
                while stack and stack[-1][0] >= level:
                    stack.pop()

                if stack:
                    stack[-1][1]['children'].append(node)
                else:
                    tree.append(node)

                stack.append((level, node))

            return {
                'has_outline': len(entries) > 0,
                'entries': entries,
                'tree': tree,
                'entry_count': len(entries),
                'page_count': doc.page_count,
            }
        finally:
            doc.close()

    # ========================================================================
    # XMP Metadata Operations
    # ========================================================================

    _RDF_NS = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'

    # Fallback prefixes for well-known XMP namespaces, used when the packet
    # does not declare a prefix for a namespace URI.
    _XMP_KNOWN_NS = {
        'http://purl.org/dc/elements/1.1/': 'dc',
        'http://ns.adobe.com/pdf/1.3/': 'pdf',
        'http://ns.adobe.com/xap/1.0/': 'xmp',
        'http://ns.adobe.com/xap/1.0/mm/': 'xmpMM',
        'http://ns.adobe.com/xap/1.0/g/': 'xmpG',
        'http://ns.adobe.com/xap/1.0/sType/ResourceRef#': 'stRef',
        'http://ns.adobe.com/xap/1.0/rights/': 'xmpRights',
        'http://ns.adobe.com/pdfx/1.3/': 'pdfx',
        'http://www.aiim.org/pdfa/ns/id/': 'pdfaid',
        'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
    }

    @classmethod
    def _qname_to_prefixed(cls, tag: str, ns_map: Dict[str, str]) -> str:
        """Convert an ElementTree ``{uri}local`` tag to ``prefix:local``."""
        if not tag.startswith('{'):
            return tag
        uri, _, local = tag[1:].partition('}')
        prefix = ns_map.get(uri) or cls._XMP_KNOWN_NS.get(uri)
        return f'{prefix}:{local}' if prefix else local

    @classmethod
    def _xmp_property_value(cls, element):
        """
        Extract the value of an XMP property element.

        Handles RDF container forms (``rdf:Alt`` / ``rdf:Seq`` / ``rdf:Bag``)
        by collecting their ``rdf:li`` items, and simple text values. An ``Alt``
        with a single language alternative collapses to a plain string.
        """
        rdf = '{' + cls._RDF_NS + '}'

        # Look for an RDF container child
        for container in ('Alt', 'Seq', 'Bag'):
            holder = element.find(rdf + container)
            if holder is not None:
                items = [
                    (li.text or '').strip()
                    for li in holder.findall(rdf + 'li')
                ]
                items = [i for i in items if i]
                if container == 'Alt' and len(items) == 1:
                    return items[0]
                return items

        text = (element.text or '').strip()
        return text or None

    @classmethod
    def extract_xmp_metadata(cls, input_path: Path) -> Dict[str, Any]:
        """
        Read and extract the XMP metadata packet of a PDF.

        XMP (Extensible Metadata Platform) is an RDF/XML packet stored in the
        document catalog (``/Metadata``). This method returns the raw packet
        as well as a parsed mapping of its properties (e.g. ``dc:title``,
        ``dc:creator``, ``pdf:Producer``, ``xmp:CreateDate``). Properties using
        RDF containers are returned as lists; single-valued properties as
        strings. The classic ``/Info`` dictionary is also returned for
        comparison.

        Args:
            input_path: Path to the PDF file

        Returns:
            Dictionary with:
            - has_xmp: Whether an XMP packet is present
            - properties: Mapping of ``prefix:name`` -> value (str or list)
            - raw: The raw XMP XML packet (or None)
            - doc_info: The classic /Info metadata dictionary
            - page_count: Number of pages in the document

        Raises:
            FileNotFoundError: If input PDF doesn't exist
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        import io
        import xml.etree.ElementTree as ET

        doc = pymupdf.open(input_path)
        try:
            raw = doc.get_xml_metadata() or ''
            doc_info = dict(doc.metadata or {})
            page_count = doc.page_count
        finally:
            doc.close()

        raw = raw.strip()
        result: Dict[str, Any] = {
            'has_xmp': bool(raw),
            'properties': {},
            'raw': raw or None,
            'doc_info': doc_info,
            'page_count': page_count,
        }

        if not raw:
            return result

        # Capture the prefix/URI declarations so original prefixes are kept.
        ns_map: Dict[str, str] = {}
        try:
            for _event, (prefix, uri) in ET.iterparse(
                io.StringIO(raw), events=('start-ns',)
            ):
                ns_map.setdefault(uri, prefix)
        except ET.ParseError:
            ns_map = {}

        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            # Packet present but unparseable — still expose the raw bytes.
            return result

        rdf = '{' + cls._RDF_NS + '}'
        properties: Dict[str, Any] = {}

        for desc in root.iter(rdf + 'Description'):
            # Compact form: properties carried as attributes
            for attr_name, attr_val in desc.attrib.items():
                if attr_name.startswith(rdf) or attr_name == 'about':
                    continue
                key = cls._qname_to_prefixed(attr_name, ns_map)
                value = attr_val.strip()
                if value:
                    properties.setdefault(key, value)

            # Element form: each child is a property
            for prop in desc:
                key = cls._qname_to_prefixed(prop.tag, ns_map)
                value = cls._xmp_property_value(prop)
                if value not in (None, '', []):
                    properties.setdefault(key, value)

        result['properties'] = properties
        return result

    @staticmethod
    def optimize_pdf(
        input_path: Path,
        output_path: Path,
        scrub_metadata: bool = True,
        subset_fonts: bool = True,
        compress_images: bool = True,
        dpi_threshold: int = 100,
        dpi_target: int = 72,
        image_quality: int = 60,
        convert_to_grayscale: bool = False,
    ) -> Dict[str, Any]:
        """
        Optimize PDF file size using PyMuPDF's compression techniques.

        This method applies three optimization techniques:
        1. Dead-weight removal - Removes metadata, thumbnails, embedded files
        2. Font subsetting - Keeps only used glyphs from embedded fonts
        3. Image compression - Downsamples and compresses images

        Args:
            input_path: Path to the input PDF file
            output_path: Path where optimized PDF should be saved
            scrub_metadata: Remove metadata, thumbnails, and embedded files
            subset_fonts: Subset embedded fonts to only used glyphs
            compress_images: Apply image compression and downsampling
            dpi_threshold: Only process images above this DPI (default: 100)
            dpi_target: Target DPI for downsampling (default: 72)
            image_quality: JPEG quality level 0-100 (default: 60)
            convert_to_grayscale: Convert images to grayscale (default: False)

        Returns:
            Dictionary with optimization results:
            - original_size: Original file size in bytes
            - optimized_size: Optimized file size in bytes
            - reduction_bytes: Size reduction in bytes
            - reduction_percent: Size reduction as percentage

        Raises:
            FileNotFoundError: If input PDF doesn't exist
            ValueError: If parameters are invalid

        Example:
            result = PdfService.optimize_pdf(
                input_path=Path("large.pdf"),
                output_path=Path("optimized.pdf"),
                compress_images=True,
                convert_to_grayscale=True
            )
            print(f"Reduced by {result['reduction_percent']:.1f}%")
        """
        if not input_path.is_file():
            raise FileNotFoundError(f'PDF file not found: {input_path}')

        if dpi_threshold < 1 or dpi_target < 1:
            raise ValueError('DPI values must be positive')

        if not 0 <= image_quality <= 100:
            raise ValueError('Image quality must be between 0 and 100')

        # Get original file size
        original_size = input_path.stat().st_size

        pdf = pymupdf.open(input_path)

        try:
            # 1. Dead-weight removal - scrub unwanted content
            if scrub_metadata:
                pdf.scrub(
                    metadata=True,  # Clear basic metadata
                    xml_metadata=True,  # Remove XML metadata
                    attached_files=True,  # Delete file attachments
                    embedded_files=True,  # Delete embedded files
                    thumbnails=True,  # Strip page thumbnails
                    reset_fields=True,  # Revert form fields to defaults
                    reset_responses=True,  # Remove annotation replies
                )

            # 2. Font subsetting - keep only used glyphs
            if subset_fonts:
                pdf.subset_fonts()

            # 3. Advanced image compression
            if compress_images:
                pdf.rewrite_images(
                    dpi_threshold=dpi_threshold,
                    dpi_target=dpi_target,
                    quality=image_quality,
                    lossy=True,  # Include lossy images
                    lossless=True,  # Include lossless images
                    bitonal=True,  # Include monochrome images
                    color=True,  # Include colored images
                    gray=True,  # Include gray-scale images
                    set_to_gray=convert_to_grayscale,  # Convert to grayscale
                )

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save with advanced compression options
            # ez_save() applies garbage=3, deflate=True, use_objstms=True
            pdf.ez_save(str(output_path))

        finally:
            pdf.close()

        # Get optimized file size
        optimized_size = output_path.stat().st_size
        reduction_bytes = original_size - optimized_size
        reduction_percent = (
            (reduction_bytes / original_size * 100) if original_size > 0 else 0
        )

        return {
            'original_size': original_size,
            'optimized_size': optimized_size,
            'reduction_bytes': reduction_bytes,
            'reduction_percent': reduction_percent,
        }

"""Utility functions for PDF manipulation."""

import re
from pathlib import Path
from typing import List, Tuple, Optional

from parxy_cli.console.console import Console

console = Console()


def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "1.5 MB"
    """
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f'{size:.1f} {unit}'
        size /= 1024.0
    return f'{size:.1f} TB'


def validate_pdf_file(file_path: str) -> Path:
    """
    Validate PDF file exists and has .pdf extension.

    Args:
        file_path: Path to PDF file

    Returns:
        Path object

    Raises:
        FileNotFoundError: if file not found
        ValueError: if file is not a PDF
    """
    path = Path(file_path)
    if not path.is_file():
        console.error(f'Input file not found: {file_path}', panel=True)
        raise FileNotFoundError(f'Input file not found: {file_path}')
    if path.suffix.lower() != '.pdf':
        console.error(f'Input file must be a PDF: {file_path}', panel=True)
        raise ValueError(f'Input file must be a PDF: {file_path}')
    return path


def is_binary_file(content: bytes) -> bool:
    """
    Detect if content is binary by checking for null bytes.

    Checks first 8KB of content for null bytes which typically
    indicate binary data.

    Args:
        content: File content as bytes

    Returns:
        True if binary, False if likely text
    """
    check_bytes = content[:8192]
    return b'\x00' in check_bytes


def parse_input_with_pages(
    input_str: str,
) -> Tuple[str, Optional[int], Optional[int]]:
    """
    Parse input string to extract file path and page range.

    Supports formats:
    - file.pdf[1] - single page (1-based)
    - file.pdf[:2] - from start to page 2 (1-based, inclusive)
    - file.pdf[3:] - from page 3 to end (1-based)
    - file.pdf[3:5] - from page 3 to 5 (1-based, inclusive)
    - file.pdf - all pages

    Args:
        input_str: Input string with optional page range

    Returns:
        Tuple of (file_path, from_page, to_page) where pages are 0-based for PyMuPDF.
        from_page and to_page are None if no range specified or represent the range to use.
    """
    # Match pattern: filename[range]
    pattern = r'^(.+?)\[([^\]]+)\]$'
    match = re.match(pattern, input_str)

    if not match:
        # No page range specified
        return input_str, None, None

    file_path = match.group(1)
    page_range = match.group(2)

    # Parse the page range
    if ':' in page_range:
        # Range format [start:end]
        parts = page_range.split(':', 1)
        start_str = parts[0].strip()
        end_str = parts[1].strip()

        # Convert to 0-based indices
        # PyMuPDF uses 0-based indexing
        from_page = (int(start_str) - 1) if start_str else 0
        to_page = (int(end_str) - 1) if end_str else None  # None means last page

    else:
        # Single page [n]
        page_num = int(page_range) - 1  # Convert to 0-based
        from_page = page_num
        to_page = page_num

    return file_path, from_page, to_page


def collect_pdf_files_with_ranges(
    inputs: List[str],
) -> List[Tuple[Path, Optional[int], Optional[int]]]:
    """
    Collect PDF files from the input list with optional page ranges.

    For folders, only files in the exact directory are collected (non-recursive).
    For files with page ranges (e.g., file.pdf[1:3]), parse and extract the range.

    Args:
        inputs: List of file paths (with optional page ranges) and/or folder paths

    Returns:
        List of tuples: (Path, from_page, to_page) where pages are 0-based.
        from_page and to_page are None if all pages should be included.
    """
    files = []

    for input_str in inputs:
        # Parse the input to extract file path and page range
        file_path_str, from_page, to_page = parse_input_with_pages(input_str)
        path = Path(file_path_str)

        if path.is_file():
            # Check if it's a PDF
            if path.suffix.lower() == '.pdf':
                files.append((path, from_page, to_page))
            else:
                console.warning(f'Skipping non-PDF file: {file_path_str}')
        elif path.is_dir():
            # Non-recursive: only files in the given directory
            # Directories cannot have page ranges
            if from_page is not None or to_page is not None:
                console.warning(
                    f'Page ranges are not supported for directories: {input_str}'
                )
            pdf_files = sorted(path.glob('*.pdf'))
            if pdf_files:
                # Add all PDFs from directory without page ranges
                files.extend([(f, None, None) for f in pdf_files])
            else:
                console.warning(f'No PDF files found in directory: {file_path_str}')
        else:
            console.warning(f'Path not found: {file_path_str}')

    return files

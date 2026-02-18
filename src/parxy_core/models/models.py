from abc import ABC
from dataclasses import dataclass
from enum import IntEnum
from io import BytesIO
from typing import List, Optional, Any, Union

from pydantic import BaseModel


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Style(BaseModel):
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    font_style: Optional[str] = None
    color: Optional[str] = None
    alpha: Optional[int] = None
    weight: Optional[float] = None


class Character(BaseModel):
    text: str
    bbox: Optional[BoundingBox] = None
    style: Optional[Style] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None

    def isEmpty(self) -> bool:
        return not self.text or self.text.strip() == ''


class Span(BaseModel):
    text: str
    bbox: Optional[BoundingBox] = None
    style: Optional[Style] = None
    characters: Optional[List[Character]] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None

    def isEmpty(self) -> bool:
        return not self.text or self.text.strip() == ''


class Line(BaseModel):
    text: str
    bbox: Optional[BoundingBox] = None
    style: Optional[Style] = None
    spans: Optional[List[Span]] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None

    def isEmpty(self) -> bool:
        return not self.text or self.text.strip() == ''


class Block(BaseModel, ABC):
    type: str
    role: Optional[str] = 'generic'
    """Document Structure role recognized for this block"""
    bbox: Optional[BoundingBox] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None
    category: Optional[str] = None
    """Category attributed to this block by the parser"""


class TextBlock(Block):
    style: Optional[Style] = None
    level: Optional[int] = None
    lines: Optional[List[Line]] = None
    text: str

    def isEmpty(self) -> bool:
        return not self.text or self.text.strip() == ''


class ImageBlock(Block):
    name: Optional[str] = None
    alt_text: Optional[str] = None


class TableBlock(Block):
    text: str

    def isEmpty(self) -> bool:
        return not self.text or self.text.strip() == ''


class Page(BaseModel):
    number: int
    width: Optional[float] = None
    height: Optional[float] = None
    blocks: Optional[List[TextBlock | ImageBlock | TableBlock]] = None
    text: str
    source_data: Optional[dict[str, Any]] = None

    def isEmpty(self) -> bool:
        return not self.text or self.text.strip() == ''


class Metadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Document(BaseModel):
    filename: Optional[str] = None
    language: Optional[str] = None
    metadata: Optional[Metadata] = None
    pages: List[Page]
    outline: Optional[List[str]] = None
    source_data: Optional[dict[str, Any]] = None
    parsing_metadata: Optional[dict[str, Any]] = None

    def isEmpty(self) -> bool:
        return all(page.isEmpty() for page in self.pages)

    def text(self, page_separator: str = '---') -> str:
        """Get the full text content of the document.

        Parameters
        ----------
        page_separator : str, optional
            String to use as separator between pages, by default "---"
            Set to empty string or None to disable page separation

        Returns
        -------
        str
            The concatenated text of all pages with optional separators
        """
        if not self.pages:
            return ''

        # Filter out empty pages
        texts = [page.text.strip() for page in self.pages if page.text]

        if not texts:
            return ''

        # Add separator between pages if specified
        if page_separator:
            return f'\n{page_separator}\n'.join(texts)

        return '\n'.join(texts)

    def contentmd(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        date: Optional[str] = None,
        license: Optional[str] = None,
        author: Optional[str] = None,
    ) -> str:
        """Get the document content formatted as content-md.

        Generates a content-md string: YAML frontmatter followed by Markdown.
        Per the spec, all heading levels are shifted up by one so the document
        title occupies the sole h1, and images use ``<figure>`` blocks.

        Parameters
        ----------
        title : str, optional
            Document title. Falls back to metadata.title, then filename.
        description : str, optional
            Short summary (~200 characters). Required by the spec; omitted from
            frontmatter when not provided.
        date : str, optional
            Creation/publication date in ISO 8601. Falls back to metadata dates.
        license : str, optional
            License name or SPDX identifier.
        author : str, optional
            Author name. Falls back to metadata.author.

        Returns
        -------
        str
            The document content formatted as content-md.
        """
        def _guess_title_from_first_page() -> Optional[str]:
            if not self.pages:
                return None
            first_page = self.pages[0]
            if not first_page.blocks:
                return None
            heading_categories = {'heading', 'title', 'header'}
            # Pick the highest-ranking heading (lowest level number) on the first page
            candidates = [
                b
                for b in first_page.blocks
                if isinstance(b, TextBlock)
                and b.category
                and b.category.lower() in heading_categories
                and b.text.strip()
            ]
            if not candidates:
                return None
            return min(candidates, key=lambda b: b.level or 1).text.strip()

        resolved_title = (
            title
            or (self.metadata.title if self.metadata else None)
            or _guess_title_from_first_page()
            or self.filename
            or 'Untitled'
        )
        resolved_date = date or (
            (self.metadata.created_at or self.metadata.updated_at)
            if self.metadata
            else None
        )
        resolved_author = author or (self.metadata.author if self.metadata else None)

        def _yaml_str(v: str) -> str:
            return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'

        fm = ['---', f'title: {_yaml_str(resolved_title)}']
        if description:
            fm.append(f'description: {_yaml_str(description)}')
        if resolved_date:
            fm.append(f'date: {_yaml_str(resolved_date)}')
        if license:
            fm.append(f'license: {_yaml_str(license)}')
        if resolved_author:
            fm.append(f'author: {_yaml_str(resolved_author)}')
        fm.append('---')
        frontmatter = '\n'.join(fm)

        if not self.pages:
            return f'{frontmatter}\n\n# {resolved_title}\n'

        parts = [f'# {resolved_title}']

        for page in self.pages:
            if not page.blocks:
                if page.text.strip():
                    parts.append(page.text.strip())
                continue

            for block in page.blocks:
                if isinstance(block, TextBlock):
                    if block.category and block.category.lower() in [
                        'heading',
                        'title',
                        'header',
                    ]:
                        # Shift all heading levels by +1 so h1 content becomes h2
                        shifted = min((block.level or 1) + 1, 6)
                        parts.append(f'{"#" * shifted} {block.text.strip()}')
                    elif block.category and block.category.lower() == 'list':
                        for line in block.text.splitlines():
                            if line.strip():
                                parts.append(f'- {line.strip()}')
                    else:
                        if block.text.strip():
                            parts.append(block.text.strip())

                elif isinstance(block, ImageBlock):
                    alt = block.alt_text or ''
                    parts.append(f'<figure>\n{alt}\n</figure>')

                elif isinstance(block, TableBlock):
                    if block.text.strip():
                        parts.append(block.text.strip())

        return f'{frontmatter}\n\n' + '\n\n'.join(parts) + '\n'

    def markdown(self) -> str:
        """Get the document content formatted as Markdown.

        The method attempts to preserve the document structure by:
        1. Converting TextBlocks to paragraphs based on their category
        2. Preserving line breaks where meaningful
        3. Adding section headers based on block levels

        Returns
        -------
        str
            The document content formatted as Markdown
        """
        if not self.pages:
            return ''

        markdown_parts = []

        for page in self.pages:
            if not page.blocks:
                if page.text.strip():
                    markdown_parts.append(page.text.strip())
                continue

            page_parts = []

            for block in page.blocks:
                if isinstance(block, TextBlock):
                    # Handle different block categories
                    if block.category and block.category.lower() in [
                        'heading',
                        'title',
                        'header',
                    ]:
                        # Determine heading level (h1-h6) based on block level or default to h2
                        level = min(block.level or 2, 6)
                        page_parts.append(f'{"#" * level} {block.text.strip()}')
                    elif block.category and block.category.lower() == 'list':
                        # Convert to bullet points
                        for line in block.text.splitlines():
                            if line.strip():
                                page_parts.append(f'- {line.strip()}')
                    else:
                        # Regular paragraph
                        if block.text.strip():
                            page_parts.append(block.text.strip())

                elif isinstance(block, ImageBlock):
                    ext = (
                        block.name.rsplit('.', 1)[-1]
                        if block.name and '.' in block.name
                        else ''
                    )
                    lang = f'image:{ext}' if ext else 'image'
                    alt = block.alt_text or ''
                    page_parts.append(f'```{lang}\n{alt}\n```')

                elif isinstance(block, TableBlock):
                    if block.text.strip():
                        page_parts.append(block.text.strip())

            if page_parts:
                markdown_parts.append('\n\n'.join(page_parts))

        return '\n\n'.join(markdown_parts)


@dataclass
class BatchTask:
    """Configuration for a single batch parsing task.

    Allows specifying per-file configuration including drivers and extraction level.

    Attributes
    ----------
    file : str | BytesIO | bytes
        The file to parse (path, URL, or binary data)
    drivers : List[str] | None
        Driver(s) to use for this file. If None, uses batch-level default
    level : str | None
        Extraction level for this file. If None, uses batch-level default

    Example
    -------
    >>> tasks = [
    ...     BatchTask(file='simple.pdf'),  # Uses defaults
    ...     BatchTask(file='complex.pdf', drivers=['llamaparse'], level='line'),
    ...     BatchTask(file=pdf_bytes, drivers=['pymupdf', 'pdfact']),
    ... ]
    >>> results = Parxy.batch(tasks)
    """

    file: Union[str, BytesIO, bytes]
    drivers: Optional[List[str]] = None
    level: Optional[str] = None


@dataclass
class BatchResult:
    """Result of a single batch parsing task.

    Attributes
    ----------
    file : str | BytesIO | bytes
        The input file that was processed
    driver : str
        The driver name used for parsing
    document : Document | None
        The parsed document, or None if an error occurred
    error : str | None
        Error message if parsing failed, None otherwise
    exception : Exception | None
        The original exception if parsing failed, None otherwise
    """

    file: Union[str, BytesIO, bytes]
    driver: str
    document: Optional['Document']
    error: Optional[str]
    exception: Optional[Exception] = None

    @property
    def success(self) -> bool:
        """Return True if parsing succeeded."""
        return self.document is not None

    @property
    def failed(self) -> bool:
        """Return True if parsing failed."""
        return self.error is not None


class HierarchyLevel(IntEnum):
    PAGE = 0
    PARAGRAPH = 1
    BLOCK = 2
    LINE = 3
    SPAN = 4
    WORD = 5
    CHARACTER = 6


def estimate_lines_from_block(
    block: TextBlock, default_font_size: float = 11
) -> TextBlock:
    """Estimate line-level layout inside a text block by splitting text and assigning bounding boxes.

    Args:
        block (TextBlock): Text block to estimate lines for.
        default_font_size (float): Default font size if not specified. Default to 11.

    Returns:
        TextBlock: The same block with its `lines` field populated.
    """
    if not block.text or not block.bbox or block.lines is not None:
        return block

    block.lines = []

    # Try to split by explicit newlines first
    raw_lines = block.text.splitlines()
    n_lines = len(raw_lines)
    # fallback: if no explicit \n but text is too long, you might want to wrap it — skipped here

    if n_lines == 0:
        raw_lines = [block.text]
        n_lines = 1

    # Estimate line height
    font_size = block.style.font_size if block.style else default_font_size
    line_height = font_size * 1.1  # 10% line spacing
    total_height = block.bbox.y1 - block.bbox.y0

    # If bbox is taller than sum of line heights, spread the lines proportionally
    if n_lines > 1:
        estimated_line_height = total_height / n_lines
    else:
        estimated_line_height = line_height

    x0 = block.bbox.x0
    x1 = block.bbox.x1
    y_top = block.bbox.y0

    for idx, line_text in enumerate(raw_lines):
        y0 = y_top + idx * estimated_line_height
        y1 = y0 + estimated_line_height
        line_bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)

        line = Line(
            text=line_text,
            bbox=line_bbox,
            style=block.style,
            page=block.page,
            source_data={'source': 'split_from_block'},
            spans=None,
        )
        block.lines.append(line)
    return block

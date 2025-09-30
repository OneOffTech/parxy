from abc import ABC
from enum import IntEnum
from typing import List, Optional, Any

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
    bbox: Optional[BoundingBox] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None


class TextBlock(BaseModel):
    type: str
    bbox: Optional[BoundingBox] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None
    category: Optional[str] = None
    style: Optional[Style] = None
    level: Optional[int] = None
    lines: Optional[List[Line]] = None
    text: str

    def isEmpty(self) -> bool:
        return not self.text or self.text.strip() == ''


class ImageBlock(Block): ...


class TableBlock(Block): ...


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
                    # Placeholder for images - could be enhanced with actual image data
                    page_parts.append('![Image]')

                elif isinstance(block, TableBlock):
                    # Placeholder for tables - could be enhanced with actual table data
                    page_parts.append('| Table content |')

            if page_parts:
                markdown_parts.append('\n\n'.join(page_parts))

        return '\n\n'.join(markdown_parts)


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

import io
from datetime import datetime
import json
from typing import List, Dict, Any

import pymupdf

from parxy_core.drivers import Driver
from parxy_core.exceptions import FileNotFoundException
from parxy_core.models import (
    BoundingBox,
    Style,
    Character,
    Span,
    Line,
    TextBlock,
    Page,
    Metadata,
    Document,
    HierarchyLevel,
)
from parxy_core.tracing import tracer


class PyMuPdfDriver(Driver):
    """PyMuPDF (fitz) driver.

    This parser reads a PDF document using PyMuPDF and converts it to a unified `Document`
    format, supporting extraction at multiple levels of detail.

    Attributes
    ----------
    supported_levels : list of str
        Supported extraction levels: `page`, `block`, `line`, `span`, `character`.
    """

    supported_levels: list[str] = ['page', 'block', 'line', 'span', 'character']

    def _handle(
        self, file: str | io.BytesIO | bytes, level: str = 'block', **kwargs
    ) -> Document | dict:
        try:
            pymupdf.TOOLS.mupdf_display_errors(False)
            pymupdf.TOOLS.mupdf_display_warnings(False)

            filename, stream = self.handle_file_input(file)
            page_key_to_extract = (
                'rawdict'
                if HierarchyLevel[level.upper()] == HierarchyLevel.CHARACTER
                else 'dict'
            )
            with self._trace_parse(filename, stream, **kwargs) as span:
                doc = pymupdf.open(stream=stream)
                doc_pages = [page.get_text(page_key_to_extract) for page in doc.pages()]
                span.set_attribute('output.document', json.dumps(doc_pages))
                span.set_attribute('output.pages', len(doc_pages))

            res = pymupdf_to_parxy(doc=doc, pages=doc_pages, level=level)
            doc.close()

            res.parsing_metadata = {'warnings': pymupdf.TOOLS.mupdf_warnings()}

        except pymupdf.FileNotFoundError as fex:
            raise FileNotFoundException(fex, self.__class__) from fex

        return res


def _parse_pdf_date(pdf_date: str) -> str | None:
    """
    Parse PDF date string to ISO format.
    PDF date format: D:YYYYMMDDHHmmSSOHH'mm'
    """
    if not pdf_date:
        return None
    try:
        # Remove prefix if present
        if pdf_date.startswith('D:'):
            pdf_date = pdf_date[2:]
        # Only take up to seconds
        dt = datetime.strptime(pdf_date[:14], '%Y%m%d%H%M%S')
        return dt.isoformat()
    except Exception:
        return None


@tracer.instrument('converting', capture_return=True)
def pymupdf_to_parxy(
    doc: pymupdf.Document, pages: List[Dict[str, Any]], level: str
) -> Document:
    """Convert a PyMuPDF Document to a `Document`.

    Parameters
    ----
    doc : pymupdf.Document
        The PyMuPDF document.
    pages: List[Dict[str, Any]]
        The serialized PyMuPDF pages.
    level : str
        Desired extraction level.

    Returns
    -------
    Document
        The converted document.
    """
    page_list = []
    for i, page in enumerate(pages):
        parxy_page = _convert_page(page=page, page_number=i + 1, level=level.upper())
        page_list.append(parxy_page)

    return Document(
        filename=doc.name,
        metadata=Metadata(
            title=doc.metadata.get('title'),
            author=doc.metadata.get('author'),
            subject=doc.metadata.get('subject'),
            keywords=doc.metadata.get('keywords'),
            creator=doc.metadata.get('creator'),
            producer=doc.metadata.get('producer'),
            created_at=_parse_pdf_date(doc.metadata.get('creationDate')),
            updated_at=_parse_pdf_date(doc.metadata.get('modDate')),
        ),
        pages=page_list,
        # outline=doc.get_toc()
    )


def _convert_bbox(bbox: list[float]) -> BoundingBox:
    """Convert a list of 4 floats into a `BoundingBox`.

    Parameters
    ----
    bbox : list of float
        [x0, y0, x1, y1] coordinates.

    Returns
    -------
    BoundingBox
        The converted bounding box.
    """
    return BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3])


def _convert_character(character: dict, page_number: int) -> Character:
    """Convert a character dict to a `Character`.

    Parameters
    ----
    character : dict
        PyMuPDF character dictionary.
    page_number : int
        Page index (0-based).

    Returns
    -------
    Character
        The converted character.
    """
    return Character(
        text=character.get('c', ''),
        bbox=_convert_bbox(character['bbox']) if 'bbox' in character else None,
        page=page_number,
        source_data={'origin': character.get('origin')},
    )


def _convert_span(
    span: dict,
    page_number: int,
    level: str,
) -> Span:
    """Convert a span dict to a `Span`.

    Parameters
    ----
    span : dict
        PyMuPDF span dictionary.
    page_number : int
        Page index.
    level : str
        Extraction level.

    Returns
    -------
    Span
        The converted span.
    """
    characters = [_convert_character(c, page_number) for c in span.get('chars', [])]
    text_characters = ''.join([c.text for c in characters])
    style = Style(
        font_name=span.get('font'),
        font_size=span.get('size'),
        font_style='italic' if span.get('flags') & pymupdf.TEXT_FONT_ITALIC else None,
        color=hex(span.get('color')) if 'color' in span else None,
        alpha=span.get('alpha'),
        weight=400 if span.get('flags') & pymupdf.TEXT_FONT_BOLD else None,
    )
    bbox = _convert_bbox(span['bbox']) if 'bbox' in span else None
    return Span(
        text=text_characters
        if HierarchyLevel[level] >= HierarchyLevel.CHARACTER
        else span.get('text', ''),
        bbox=bbox,
        style=style,
        characters=characters
        if HierarchyLevel[level] >= HierarchyLevel.CHARACTER
        else None,
        page=page_number,
        source_data={
            'flags': span.get('flags'),
            'bidi': span.get('bidi'),
            'char_flags': span.get('char_flags'),
            'ascender': span.get('ascender'),
            'descender': span.get('descender'),
            'origin': span.get('origin'),
        },
    )


def _convert_line(
    line: dict,
    page_number: int,
    level: str,
) -> Line:
    """Convert a line dict to a `Line`.

    Parameters
    ----
    line : dict
        PyMuPDF line dictionary.
    page_number : int
        Page index.
    level : str
        Extraction level.

    Returns
    -------
    Line
        The converted line.
    """
    spans = [_convert_span(span, page_number, level) for span in line.get('spans', [])]
    text = ''.join(span.text for span in spans)
    bbox = _convert_bbox(line['bbox']) if 'bbox' in line else None
    return Line(
        text=text,
        bbox=bbox,
        spans=spans if HierarchyLevel[level] >= HierarchyLevel.SPAN else None,
        page=page_number,
        source_data={'wmode': line.get('wmode'), 'dir': line.get('dir')},
    )


def _convert_text_block(
    text_block: dict,
    page_number: int,
    level: str,
) -> TextBlock:
    """Convert a text block dict to a `TextBlock`.

    Parameters
    ----
    text_block : dict
        PyMuPDF block dictionary.
    page_number : int
        Page index.
    level : str
        Extraction level.

    Returns
    -------
    TextBlock
        The converted text block.
    """
    if text_block.get('type') != 0:
        raise ValueError('Block is not a text block')
    lines = [
        _convert_line(line, page_number, level) for line in text_block.get('lines', [])
    ]
    block_text = '\n'.join(line.text for line in lines)
    return TextBlock(
        type='text',
        bbox=_convert_bbox(text_block['bbox']) if 'bbox' in text_block else None,
        page=page_number,
        lines=lines if HierarchyLevel[level] >= HierarchyLevel.LINE else None,
        text=block_text,
        source_data={'number': text_block.get('number')},
    )


def _convert_page(
    page: Dict[str, Any],
    page_number: int,
    level: str,
) -> Page:
    """Convert a PyMuPDF Page into a `Page`.

    Parameters
    ----
    page : Dict[str, Any]
        The PyMuPDF Page object serialized as dictionary.
    page_number : int
        Page index (0-based).
    level : str
        Desired extraction level (`block`, `line`, `span`, `character`).

    Returns
    -------
    Page
        The converted page.
    """
    blocks = [
        _convert_text_block(block, page_number, level)
        for block in page.get('blocks', [])
        if block.get('type') == 0
    ]
    page_text = '\n'.join(block.text for block in blocks)
    return Page(
        number=page_number,
        width=page.get('width'),
        height=page.get('height'),
        blocks=blocks if HierarchyLevel[level] >= HierarchyLevel.BLOCK else None,
        text=page_text,
    )

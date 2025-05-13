import pymupdf
from camel_converter import dict_to_snake

from text_extractor.models import BoundingBox, Character, Span, Style, Line, TextBlock, Page, Document
from text_extractor.models.document import Metadata
from text_extractor.parser.pdf_parser import PDFParser


class PymupdfParser(PDFParser):

    def parse(self, filename: str, **kwargs) -> Document:
        # The interface should always use page.get_text("dict") for all detail levels,
        # except for characther in which case "rawdict" should be used.
        doc = pymupdf.open(filename)
        return pymupdf_to_parxy(doc=doc)


def pymupdf_to_parxy(doc: pymupdf.Document) -> Document:
    page_list = []
    for i, page in enumerate(doc):
        parxy_page = _convert_page(page=page, page_number=i)
        page_list.append(parxy_page)
    return Document(filename=doc.name,
                    metadata=Metadata(**dict_to_snake(doc.metadata)),
                    pages=page_list,
                    outline=doc.get_toc())


def _convert_bbox(
        bbox: list[float]
) -> BoundingBox:
    return BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3])


def _convert_charachter(
        charachter: dict,
        page_number: int
) -> Character:
    return Character(
        text=charachter.get("c", ""),
        bbox=_convert_bbox(charachter["bbox"]) if "bbox" in charachter else None,
        page=page_number,
        source_data={"origin": charachter.get("origin")},
    )


def _convert_span(
        span: dict,
        page_number: int
) -> Span:
    characters = [_convert_charachter(c, page_number) for c in span.get("chars", [])] if "chars" in span else None
    style = Style(
        font_name=span.get("font"),
        font_size=span.get("size"),
        font_style="italic" if span.get("flags") & pymupdf.TEXT_FONT_ITALIC else None,
        color=hex(span.get("color")) if "color" in span else None,
        alpha=span.get("alpha"),
        weight=400 if span.get("flags") & pymupdf.TEXT_FONT_BOLD else None,
    )
    bbox = _convert_bbox(span["bbox"]) if "bbox" in span else None
    return Span(
        text=span.get("text", ""),
        bbox=bbox,
        style=style,
        characters=characters,
        page=page_number,
        source_data={"flags": span.get("flags"),
                     "bidi": span.get("bidi"),
                     "char_flags": span.get("char_flags"),
                     "ascender": span.get("ascender"),
                     "descender": span.get("descender"),
                     "origin": span.get("origin")},
    )


def _convert_line(
        line: dict,
        page_number: int
) -> Line:
    spans = [_convert_span(span, page_number) for span in line.get("spans", [])]
    text = "".join(span.text for span in spans)
    bbox = _convert_bbox(line["bbox"]) if "bbox" in line else None
    return Line(
        text=text,
        bbox=bbox,
        spans=spans,
        page=page_number,
        source_data={"wmode": line.get("wmode"), "dir": line.get("dir")},
    )


def _convert_text_block(
        text_block: dict,
        page_number: int
) -> TextBlock:
    if text_block.get("type") != 0:
        raise ValueError("Block is not a text block")
    lines = [_convert_line(line, page_number) for line in text_block.get("lines", [])]
    block_text = "\n".join(line.text for line in lines)
    return TextBlock(
        type="text",
        bbox=_convert_bbox(text_block["bbox"]) if "bbox" in text_block else None,
        page=page_number,
        lines=lines,
        text=block_text,
        source_data={"number": text_block.get("number")}
    )


def _convert_page(
        page: pymupdf.Page,
        page_number: int
) -> Page:
    """Convert a PyMuPDF Page into a Parxy Page object.

    Parameters
    ----------
    page : dict
        The PyMuPDF Page object following the format specified in the PyMuPDF documentation at
        https://pymupdf.readthedocs.io/en/latest/page.html#.
    page_number: int
        The progressive numeration of the page (0-based).

    Returns
    -------
    Page
        The converted Parxy Page object.
    """
    text_page = page.get_text("dict")
    blocks = [_convert_text_block(block, page_number)
              for block in text_page.get("blocks", [])
              if block.get("type") == 0]
    page_text = "\n".join(block.text for block in blocks)
    return Page(
        number=page_number,
        width=text_page.get("width"),
        height=text_page.get("height"),
        blocks=blocks,
        text=page_text,
        source_data={"fonts": page.get_fonts()}
    )

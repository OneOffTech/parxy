import pymupdf

from text_extractor.models import BoundingBox, Character, Span, Style, Line, TextBlock, Page, Document
from text_extractor.parser.pdf_parser import PDFParser


class PymupdfParser(PDFParser):

    def parse(self, filename: str, **kwargs) -> Document:
        # The interface should always use page.get_text("dict") for all detail levels,
        # except for characther in which case "rawdict" should be used.
        pdf = pymupdf.open(filename)
        page_list = []
        for i, page in enumerate(pdf):
            tmp_page = convert_page(page.get_text("dict"), i)
            page_list.append(tmp_page)
        return Document(pages=page_list)


def convert_bbox(bbox: list[float]) -> BoundingBox:
    return BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3])


def convert_char(c: dict, page_number: int) -> Character:
    return Character(
        text=c.get("c", ""),
        bbox=convert_bbox(c["bbox"]) if "bbox" in c else None,
        page=page_number,
        source_data=c,
    )


def convert_span(span: dict, page_number: int) -> Span:
    characters = [convert_char(c, page_number) for c in span.get("chars", [])] if "chars" in span else None
    style = Style(
        font_name=span.get("font"),
        font_size=span.get("size"),
        color=hex(span.get("color")) if "color" in span else None,
        # TODO: Parse also flags
    )
    return Span(
        text=span.get("text", ""),
        bbox=convert_bbox(span["bbox"]) if "bbox" in span else None,
        style=style,
        characters=characters,
        page=page_number,
        source_data=span
    )


def convert_line(line: dict, page_number: int) -> Line:
    spans = [convert_span(span, page_number) for span in line.get("spans", [])]
    text = "".join(span.text for span in spans)
    return Line(
        text=text,
        bbox=convert_bbox(line["bbox"]) if "bbox" in line else None,
        spans=spans,
        page=page_number,
        source_data=line
    )


def convert_text_block(text_block: dict, page_number: int) -> TextBlock:
    if text_block.get("type") != 0:
        raise ValueError("Block is not a text block")
    lines = [convert_line(line, page_number) for line in text_block.get("lines", [])]
    block_text = "\n".join(line.text for line in lines)

    return TextBlock(
        type="text",
        bbox=convert_bbox(text_block["bbox"]) if "bbox" in text_block else None,
        page=page_number,
        source_data=text_block,
        category=None,
        level=None,
        lines=lines,
        text=block_text
    )


def convert_page(page: dict, page_number: int) -> Page:
    blocks = [convert_text_block(block, page_number) for block in page.get("blocks", []) if block.get("type") == 0]
    page_text = "\n".join(block.text for block in blocks)
    return Page(text=page_text, number=page_number, blocks=blocks)

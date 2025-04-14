from typing import Literal

import pymupdf
from parse_document_model import Document, Page
from parse_document_model.attributes import BoundingBox, TextAttributes
from parse_document_model.document import Text
from parse_document_model.marks import Font, TextStyleMark, Color

from text_extractor.parser.pdf_parser import PDFParser


class PymupdfParser(PDFParser):
    def parse(self, filename: str, **kwargs) -> Document:
        pdf = pymupdf.open(filename)
        page_list = []
        for i, page in enumerate(pdf):
            page_nodes = []
            for block in page.get_text("dict")["blocks"]:
                if block["type"] == 0:
                    text = span_to_texts(block, page=i + 1)
                    page_nodes.extend(text)
            page_list.append(Page(content=page_nodes))
        return Document(content=page_list)


def span_to_texts(block: dict, page: int) -> list[Text]:
    res = []
    text_marks = set()
    bboxes = []
    content = ""
    for line in block["lines"]:
        for span in line["spans"]:
            font = Font(id=span["font"], name=span["font"], size=int(span["size"]))
            color = hex_to_rgb(span["color"])
            text_marks.add(TextStyleMark(category="textStyle",
                                         font=font,
                                         color=Color(id=hex(span["color"]),
                                                     r=color[0], g=color[1], b=color[2])))
            # font_type_mark = Mark(category=flag_to_mark(span["flags"]))
            bboxes.append(BoundingBox(min_x=span["bbox"][0],
                                      min_y=span["bbox"][1],
                                      max_x=span["bbox"][2],
                                      max_y=span["bbox"][3],
                                      page=page))
            content += span["text"]
        content += " "

    if len(content.strip()) == 0:
        return res

    text = Text(content=content,
                category="body",
                attributes=TextAttributes(bounding_box=bboxes),
                marks=list(text_marks))
    res.append(text)
    return res


def flag_to_mark(flag: int) -> Literal["superscripted", "italic", "serifed", "monospaced", "bold"]:
    pass


def hex_to_rgb(hex_color: int) -> tuple[int, int, int]:
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    return r, g, b

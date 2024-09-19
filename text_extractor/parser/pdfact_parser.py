import logging
from typing import List, Dict
from collections import Counter

import requests
from requests.exceptions import RequestException

from text_extractor.models import Document, Color, Font, Attributes, BoundingBox, Content, NodeAttributes, Node
from text_extractor.models.marks import Mark, TextStyleMark
from text_extractor.parser.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class PdfactParser(PDFParser):
    def __init__(self, url: str) -> None:
        self.url = url

    def parse(self, filename: str, **kwargs) -> Document:
        body = {"url": filename}
        unit = kwargs.get("unit", None)
        roles = kwargs.get("roles", None)
        if unit is not None:
            body["unit"] = unit
        if roles is not None:
            body["roles"] = roles
        try:
            response = requests.post(self.url, json=body)
            response.raise_for_status()
            res = response.json()
            if unit == 'paragraph' or unit is None:
                res = pdfact_formatter(res)
                res = heading_filter(res)
            document = pdfact_to_document(res)
            document = determine_heading_level(document)
            return document
        except RequestException as e:
            logger.exception(f"An error occurred while trying to reach the API: {e}", exc_info=True)
            raise e


def pdfact_to_document(json_data: dict) -> Document:
    colors = [Color(**color) for color in json_data.get('colors', [])]
    fonts = [Font(**font) for font in json_data.get('fonts', [])]
    pages: Dict[int, List[Content]] = {}

    for para in json_data.get('paragraphs', []):
        paragraph_detail = para['paragraph']
        page = paragraph_detail['positions'][0]['page'] if paragraph_detail.get('positions') else None
        color_id = paragraph_detail['color']['id']
        color = next((c for c in colors if c.id == color_id), None)

        font_id = paragraph_detail['font']['id']
        font_size = paragraph_detail['font']['font-size']
        original_font = next((f for f in fonts if f.id == font_id), None)

        if original_font and font_size:
            font = Font(name=original_font.name, id=original_font.id, size=round(font_size))
        else:
            font = original_font

        font_info = next((font for font in json_data.get('fonts', []) if font.get('id') == font_id), None)

        is_bold = False
        is_italic = False
        if font_info:
            is_bold = font_info.get('is-bold')
            is_italic = font_info.get('is-italic')

        # TODO implement logic for links
        marks = []
        if color or font:
            mark = TextStyleMark(category='textStyle', color=color, font=font)
            marks.append(mark)
        if is_bold:
            mark = Mark(category='bold')
            marks.append(mark)
        if is_italic:
            mark = Mark(category='italic')
            marks.append(mark)

        bounding_boxs = [
            BoundingBox(
                min_x=pos['minX'],
                min_y=pos['minY'],
                max_x=pos['maxX'],
                max_y=pos['maxY'],
                page=pos['page']
            ) for pos in paragraph_detail.get('positions', [])
        ]

        attributes = Attributes(bounding_box=bounding_boxs)

        content = Content(
            role=paragraph_detail['role'],
            text=paragraph_detail['text'],
            marks=marks,
            attributes=attributes
        )

        if page not in pages:
            pages[page] = []
        pages[page].append(content)

    nodes = [
        Node(
            attributes=NodeAttributes(page=page),
            content=content_list
        ) for page, content_list in pages.items()
    ]

    doc = Document(
        content=nodes
    )

    return doc


def pdfact_formatter(json_file):
    previous_length = None
    current_json = json_file
    current_length = len(current_json["paragraphs"])

    while previous_length is None or previous_length != current_length:
        previous_length = current_length
        current_json = aggregate_paragraphs(current_json)
        current_length = len(current_json["paragraphs"])

    return current_json


def aggregate_paragraphs(json_file):
    output = []
    fonts = json_file["fonts"]
    colors = json_file["colors"]
    i = 0

    # Base case: if the document consists of only one paragraph, the method terminates and returns the unmodified JSON
    if len(json_file["paragraphs"]) == 1:
        return json_file

    while i < len(json_file["paragraphs"][:-1]):
        paragraph1 = json_file["paragraphs"][i]
        paragraph2 = json_file["paragraphs"][i + 1]

        if compare_paragraphs(paragraph1, paragraph2):
            paragraph = merge_pargraphs(paragraph1, paragraph2)
            output.append(paragraph)

            # After merging the two paragraphs, proceed to the paragraph following the (i+1)-th one
            if i + 2 < len(json_file["paragraphs"][:-1]):
                i += 2
                continue
            # if the paragraph following the (i+1)-th one is the last one, then concatenate it
            elif i + 2 == len(json_file["paragraphs"][:-1]):
                output.append(json_file["paragraphs"][i + 2])
                break
            # If there is no paragraph following the (i+1)-th one, terminate
            elif i + 2 > len(json_file["paragraphs"][:-1]):
                break
        else:
            output.append(json_file["paragraphs"][i])

            # If the next paragraph is the last one, then concatenate it to the list of paragraphs
            if i + 1 == len(json_file["paragraphs"][:-1]):
                output.append(json_file["paragraphs"][i + 1])
        i += 1

    paragraphs = {'fonts': fonts, 'paragraphs': output, 'colors': colors}
    return paragraphs


def compare_paragraphs(p1, p2, tr=25):
    if p1["paragraph"]["role"] != p2["paragraph"]["role"]:
        return False
    if p1["paragraph"]["color"] != p2["paragraph"]["color"]:
        return False
    if p1["paragraph"]["font"] != p2["paragraph"]["font"]:
        return False

    positions1, positions2 = p1["paragraph"]["positions"], p2["paragraph"]["positions"]

    for pos1 in positions1:
        for pos2 in positions2:
            # Compare if they are aligned with respect to the x-axis and if their distance is less than a threshold
            if (pos1["minX"] - pos2["minX"] == 0
                or pos1["maxX"] - pos2["maxX"] == 0
                or (pos1["minX"] + pos1["maxX"]) / 2 == (pos2["minX"] + pos2["maxX"]) / 2) \
                    and (pos1["minY"] - pos2["maxY"] < tr):
                return True
            # Compare if they are aligned with respect to the y-axis and if their distance is less than a threshold
            elif (pos1["minY"] - pos2["minY"] == 0
                  or pos1["maxY"] - pos2["maxY"] == 0
                  or (pos1["minY"] + pos1["maxY"]) / 2 == (pos2["minY"] + pos2["maxY"]) / 2) \
                    and (pos2["minX"] - pos1["maxX"] < tr):
                return True

    return False


def merge_pargraphs(p1, p2):
    role = p1["paragraph"]["role"]
    color = p1["paragraph"]["color"]
    font = p1["paragraph"]["font"]
    positions1 = p1["paragraph"]["positions"]
    positions2 = p2["paragraph"]["positions"]
    text1 = p1["paragraph"]["text"]
    text2 = p2["paragraph"]["text"]

    paragraph = {
        "paragraph": {
            "role": role,
            "color": color,
            "positions": positions1 + positions2,
            "text": text1 + '\n\n' + text2,
            "font": font
        }
    }

    return paragraph


def heading_filter(json_file):
    font_size_body = [paragraph["paragraph"]["font"]["font-size"] for paragraph in json_file["paragraphs"] if
                      paragraph["paragraph"]["role"] == "body"]
    if len(font_size_body) == 0:
        return json_file
    min_font_size_body = min(font_size_body)
    for i in range(len(json_file["paragraphs"])):
        paragraph = json_file["paragraphs"][i]
        if paragraph["paragraph"]["role"] == "heading":
            font_size = paragraph["paragraph"]["font"]["font-size"]
            if font_size == min_font_size_body:
                paragraph["paragraph"]["role"] = "body"
    return json_file


def determine_heading_level(document: Document) -> Document:
    """
    Determines the heading level based on the font style (font name and font size) of headings in the document.

    The function iterates over each page and each node of the document to identify headings and collects their font
    styles. These styles are then sorted by font size in descending order, assuming that larger font sizes correspond
    to higher-level headings. Finally, the headings are assigned levels based on their font styles.

    :param document: The input document object, which contains content in the form of pages and nodes. Each node
                            represents an element in the document.

    :return: The document with updated heading levels assigned to each heading node.
    """
    heading_styles = []

    for page in document.content:
        for node in page.content:
            if node.role == "heading" and node.marks:
                marks = node.marks
                font_name = None
                font_size = None

                for mark in marks:
                    if mark.category == 'textStyle':
                        font_name = mark.font.name
                        font_size = mark.font.size

                if font_name and font_size:
                    # Avoid duplicates: only add new styles
                    existing_style = next((style for style in heading_styles if
                                           style['font_name'] == font_name and style['font_size'] == font_size), None)
                    if not existing_style:
                        heading_styles.append({
                            'font_name': font_name,
                            'font_size': font_size,
                            'occurrences': 1
                        })
                    else:
                        existing_style['occurrences'] += 1
    # Sort the styles by font size in descending order
    heading_styles = sorted(heading_styles, key=lambda x: x['font_size'], reverse=True)

    largest_font_style = heading_styles[0] if heading_styles else None
    if largest_font_style and largest_font_style['occurrences'] == 1:
        heading_styles = heading_styles[1:]
    # Assign levels to the sorted heading styles
    assigned_levels = assign_heading_levels(heading_styles)

    for page in document.content:
        for node in page.content:
            if node.role == "heading" and node.marks:
                marks = node.marks
                font_name = None
                font_size = None

                for mark in marks:
                    if mark.category == 'textStyle':
                        font_name = mark.font.name
                        font_size = mark.font.size

                if font_name and font_size:
                    if (largest_font_style and
                            largest_font_style['font_name'] == font_name and
                            largest_font_style['font_size'] == font_size):
                        node.role = "title"
                    else:
                        level = 4
                        for style in assigned_levels:
                            if style['font_name'] == font_name and style['font_size'] == font_size:
                                level = style['level']
                                break
                        node.role = f"{node.role} {level}"

    return document


def assign_heading_levels(heading_styles):
    # Count the number of occurrences for each font
    font_count = Counter([font['font_name'] for font in heading_styles])

    main_font = font_count.most_common(1)[0][0]
    main_fonts = sorted([f for f in heading_styles if f['font_name'] == main_font],
                        key=lambda x: -x['font_size'])
    other_fonts = [f for f in heading_styles if f['font_name'] != main_font]
    levels_assigned = {}
    for i, font in enumerate(main_fonts):
        level = min(i + 1, 4)
        levels_assigned[(font['font_name'], font['font_size'])] = level

    for font in other_fonts:
        size = font['font_size']
        same_size_fonts = [f for f in levels_assigned if f[1] == size]

        if same_size_fonts:
            level = levels_assigned[same_size_fonts[0]]
        else:
            existing_sizes = sorted([f[1] for f in levels_assigned])

            if size > existing_sizes[-1]:
                level = 1
            elif size < existing_sizes[0]:
                level = 4
            else:
                for i in range(len(existing_sizes) - 1):
                    if existing_sizes[i + 1] > size > existing_sizes[i]:
                        mid_point = (existing_sizes[i] + existing_sizes[i + 1]) / 2
                        if size >= mid_point:
                            level = levels_assigned[(main_font, existing_sizes[i + 1])]
                        else:
                            level = levels_assigned[(main_font, existing_sizes[i])]
                        break

        levels_assigned[(font['font_name'], font['font_size'])] = level

    result = []
    for font in heading_styles:
        font_info = {
            'font_name': font['font_name'],
            'font_size': font['font_size'],
            'level': levels_assigned[(font['font_name'], font['font_size'])]
        }
        result.append(font_info)

    return result

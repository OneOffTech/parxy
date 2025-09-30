import io
from typing import Optional

import requests
import validators

from urllib.parse import urljoin

from parxy_core.drivers import Driver
from parxy_core.models import (
    BoundingBox,
    Style,
    Character,
    Span,
    TextBlock,
    Page,
    Document,
)


class PdfActDriver(Driver):
    """PdfAct service driver.

    This parser interacts with the PdfAct API to extract page-level and paragraph-level
    text and layout from PDF documents.

    Attributes
    ----------
    supported_levels : list of str
        The supported extraction levels: `page`, `paragraph` (`span` and `character` levels will be added soon).
    base_url : str
        URL of the PdfAct API endpoint.
    """

    DEFAULT_API_PATH = 'api/pdf/parse'

    supported_levels: list[str] = ['page', 'paragraph', 'block']

    ___base_url: str

    ___api_key: Optional[str] = None

    def _initialize_driver(self):
        """Initialize PdfAct driver."""

        if validators.url(self._config.get('base_url'), simple_host=True) != True:
            # simple_host=True allow validation of localhost URLs https://github.com/python-validators/validators/issues/285#issuecomment-1676336214
            raise ValueError(
                f'Invalid base URL. Expected URL, found [{self._config.get("base_url")}].'
            )

        self.__api_key = self._config.get('api_key')
        self.__base_url = self._config.get('base_url')

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'block',
    ) -> Document:
        res = self._request(file, level)

        return pdfact_to_parxy(doc=res, level=level, filename=file)

    def __api_url(self) -> str:
        return urljoin(self.__base_url, self.DEFAULT_API_PATH)

    def _request(self, file: str | io.BytesIO | bytes, level: str) -> dict:
        """Send a request to the PdfAct service.

        Parameters
        ----
        file : str | io.BytesIO | bytes
            Path or URL to the PDF file.
        level : str
            Desired extraction level.

        Returns
        -------
        dict
            Raw JSON response from the PdfAct API.
        """
        units = [
            'page',
            'paragraph',
        ]  # We always want to also retrieve info about the page

        if isinstance(file, (io.BytesIO, bytes)):
            raise NotImplementedError('The given input file is not supported.')

        if not isinstance(file, str):
            raise ValueError('File parameter must be a `str`.')

        if validators.url(file) is True:
            body = {'url': file, 'unit': ','.join(units)}
            res = requests.post(self.__api_url(), json=body)
            # TODO: set authentication as bearer when __api_key is not none
        else:
            # Send the file as multipart upload
            with open(file, 'rb') as f:
                res = requests.post(
                    self.__api_url(), files={'file': f}, data={'unit': ','.join(units)}
                )

        res.raise_for_status()
        return res.json()

    def getHost(self) -> str:
        return self.__host

    def isSecured(self) -> bool:
        return self.__api_key is not None


def pdfact_to_parxy(doc: dict, level: str, filename: str) -> Document:
    """Convert a raw PdfAct response to a `Document`.

    Parameters
    ----
    doc : dict
        Raw response from PdfAct.
    level : str
        Extraction level (`page` or `paragraph`).
    filename : str
        The original filename of the PDF.

    Returns
    -------
    Document
        Converted document in the unified format.
    """
    fonts_lookup = {font['id']: font for font in doc.get('fonts', [])}
    colors_lookup = {color['id']: color for color in doc.get('colors', [])}

    # Init empty pages
    pages = []
    for page in doc.get('pages', []):
        pages.append(
            Page(
                number=page['id'],
                width=page['width'],
                height=page['height'],
                blocks=[],
                text='',
            )
        )

    # Loop over blocks to extract text
    for element in doc.get('paragraphs', []):
        parxy_element = _convert_text_block(
            element, fonts=fonts_lookup, colors=colors_lookup
        )
        current_page = parxy_element.page - 1
        pages[current_page].blocks.append(parxy_element)
        if pages[current_page].text != '':
            pages[current_page].text += '\n'
        pages[current_page].text += parxy_element.text

    return Document(
        filename=filename,
        pages=pages,
    )


def _convert_bbox(bboxes: list[dict]) -> Optional[BoundingBox]:
    """Convert a list of PdfAct bounding boxes to a `BoundingBox`.

    Parameters
    ----
    bboxes : list of dict
        List of bounding box dicts with `minX`, `minY`, `maxX`, `maxY`.

    Returns
    -------
    BoundingBox or None
        The combined bounding box or None if empty.
    """
    if len(bboxes) == 0:
        return None
    min_x = min(bbox['minX'] for bbox in bboxes)
    min_y = min(bbox['minY'] for bbox in bboxes)
    max_x = max(bbox['maxX'] for bbox in bboxes)
    max_y = max(bbox['maxY'] for bbox in bboxes)
    return BoundingBox(x0=min_x, y0=min_y, x1=max_x, y1=max_y)


def _convert_character(
    character: dict,
) -> Character:
    """Convert a PdfAct character dict to a `Character`.

    Parameters
    ----
    character : dict
        PdfAct character dict.

    Returns
    -------
    Character
        Converted character.
    """
    char_data = character.get('character', {})
    positions = char_data.get('positions', [])
    font = char_data.get('font', {})
    color = char_data.get('color', {})
    style = Style(
        font_name=font.get('id'),
        font_size=font.get('font-size'),
        color=color.get('id'),
    )
    return Character(
        text=char_data.get('text', ''),
        bbox=_convert_bbox(positions),
        style=style,
        page=positions[0]['page'] if len(positions) > 0 else None,
    )


def _convert_span(
    span: dict,
) -> Span:
    """Convert a PdfAct word span dict to a `Span`.

    Parameters
    ----
    span : dict
        PdfAct span dict.

    Returns
    -------
    Span
        Converted span.
    """
    word = span.get('word', {})
    positions = word.get('positions', [])
    font = word.get('font', {})
    color = word.get('color', {})

    style = Style(
        font_name=font.get('id'),
        font_size=font.get('font-size'),
        color=color.get('id'),
    )
    return Span(
        text=word.get('text', ''),
        bbox=_convert_bbox(positions),
        style=style,
        page=positions[0]['page'] if len(positions) > 0 else None,
    )


def _convert_text_block(
    text_block: dict,
    fonts: dict,
    colors: dict,
) -> TextBlock:
    """Convert a PdfAct paragraph dict to a `TextBlock`.

    Parameters
    ----
    text_block : dict
        PdfAct paragraph element.
    fonts : dict
        Lookup table of fonts from PdfAct response.
    colors : dict
        Lookup table of colors from PdfAct response.

    Returns
    -------
    TextBlock
        Converted text block.
    """
    data = text_block.get('paragraph')
    text = data.get('text', '')
    category = data.get('role') if 'role' in data else None
    positions = data.get('positions', [])

    # Convert font and color
    font_id = data.get('font', {}).get('id')
    pdfact_font = fonts.get(font_id)
    color_id = data.get('color', {}).get('id')
    pdfact_color = colors.get(color_id)
    style = Style(
        font_name=pdfact_font.get('name'),
        font_size=data.get('font', {}).get('size'),
        font_style='italic' if pdfact_font.get('is-italic') else None,
        color='0x{:02x}{:02x}{:02x}'.format(
            pdfact_color.get('r'), pdfact_color.get('g'), pdfact_color.get('b')
        ),
        weight=400 if pdfact_font.get('is-bold') else None,
    )

    page = min([pos['page'] for pos in positions])
    bbox = _convert_bbox([pos for pos in positions if pos['page'] == page])
    return TextBlock(
        type='text',
        bbox=bbox,
        style=style,
        page=page,
        source_data={'positions': positions},
        category=category,
        text=text,
    )

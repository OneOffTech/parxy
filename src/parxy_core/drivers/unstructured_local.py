import io

import validators

from typing import TYPE_CHECKING

# Type hints that will be available at runtime when unstructured is installed
if TYPE_CHECKING:
    from unstructured.documents.elements import Element as UnstructuredElement
    from unstructured.documents.elements import Text as UnstructuredText
else:
    # Placeholder types for when package is not installed
    UnstructuredElement = object
    UnstructuredText = object


from parxy_core.drivers import Driver
from parxy_core.exceptions import FileNotFoundException, ParsingException
from parxy_core.models import Document, TextBlock, BoundingBox, Page, HierarchyLevel


class UnstructuredLocalDriver(Driver):
    """Parser implementation using the `unstructured` library.

    This parser reads a document using Unstructured partitioning and converts it into the unified `Document` format,
    supporting `page` and `paragraph` levels of detail.

    Attributes
    ----------
    supported_levels : list of str
        Supported extraction levels: `page`, `paragraph`.
    """

    supported_levels: list[str] = ['page', 'block']

    def _initialize_driver(self):
        """Initialize the Unstructured driver."""

        try:
            from unstructured.partition.auto import partition

            self.__client = partition
        except ImportError as e:
            raise ImportError(
                'Unstructured dependencies not installed. '
                "Install with 'pip install parxy-core[unstructured_local]'"
            ) from e

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'paragraph',
        **kwargs,
    ) -> Document:
        """Parse a document using `unstructured` into the unified `Document` format.

        Parameters
        ----------
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level: `page` or `paragraph`. Default is `"paragraph"`.
        raw : bool, optional
            If True, returns the raw output of `unstructured.partition.auto.partition`. Default is False.
        **kwargs : dict
            Additional keyword arguments passed to `unstructured.partition.auto.partition`.

        Returns
        -------
        Document or list of Element
            The parsed document or the raw list of `unstructured` elements.
        """

        if level == 'block':
            level = 'paragraph'

        url, stream = None, None
        if isinstance(file, str):
            if validators.url(file) is True:
                url = file
                file = None
        elif isinstance(file, io.BytesIO):
            stream = file
            file = ''
        elif isinstance(file, bytes):
            stream = io.BytesIO(file)
            file = ''

        try:
            res = self.__client(filename=file, url=url, file=stream, **kwargs)
        except FileNotFoundError as fex:
            raise FileNotFoundException(fex, self.__class__) from fex
        except Exception as wex:
            if isinstance(wex, FileNotFoundException):
                raise wex
            raise ParsingException(
                wex.error_message(), self.__class__, details=wex.value
            ) from wex

        return unstructured_to_parxy(doc=res, level=level)


def unstructured_to_parxy(
    doc: list[UnstructuredElement],
    level: str,
) -> Document:
    """Convert a list of `unstructured` Elements to a unified `Document`.

    Parameters
    ----------
    doc : list of Element
        The list of elements returned by `unstructured.partition.auto.partition`.
    level : str
        Desired extraction level: `page` or `paragraph`.

    Returns
    -------
    Document
        The converted document.
    """
    level = level.upper()
    pages = [
        Page(
            number=i,
            text='',
            blocks=[] if HierarchyLevel[level] >= HierarchyLevel.PARAGRAPH else None,
        )
        for i in range(doc[-1].metadata.page_number)
    ]
    for el in doc:
        if not isinstance(el, UnstructuredText):
            continue  # Not supported yet
        if HierarchyLevel[level] >= HierarchyLevel.PARAGRAPH:
            parxy_element = _convert_text_block(el)
            pages[parxy_element.page].blocks.append(parxy_element)
        current_page = el.metadata.page_number - 1
        if pages[current_page].text != '':
            pages[current_page].text += '\n'
        pages[current_page].text += el.text
    return Document(
        filename=doc[0].metadata.filename,
        language=doc[0].metadata.languages[0] if doc[0].metadata.languages else None,
        pages=pages,
    )


def _convert_text_block(
    text_block: UnstructuredText,
) -> TextBlock:
    """Convert an `unstructured` Text element to a `TextBlock`.

    Parameters
    ----------
    text_block : Text
        The `unstructured` Text element.

    Returns
    -------
    TextBlock
        The converted text block.
    """
    x0, y0 = text_block.metadata.coordinates.points[0]
    x2, y2 = text_block.metadata.coordinates.points[2]
    bbox = BoundingBox(x0=x0, y0=y0, x1=x2 - x0, y1=y2 - y0)
    return TextBlock(
        type='text',
        bbox=bbox,
        category=text_block.category,
        text=text_block.text,
        page=text_block.metadata.page_number - 1,
        source_data=text_block.metadata.to_dict(),
    )

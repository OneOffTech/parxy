import io
from typing import TYPE_CHECKING

# Type hints that will be available at runtime when llama_cloud_services is installed
if TYPE_CHECKING:
    from llama_cloud_services import LlamaParse
    from llama_cloud_services.parse.types import JobResult, PageItem, Page as LlamaPage
else:
    # Placeholder types for when package is not installed
    LlamaParse = None
    JobResult = object
    PageItem = object
    LlamaPage = object

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page, BoundingBox, TextBlock, HierarchyLevel
from parxy_core.exceptions import (
    ParsingException,
    AuthenticationException,
    FileNotFoundException,
)


class LlamaParseDriver(Driver):
    """Llama Cloud Services document processing via LlamaParse API.

    This parser interacts with the LlamaParse cloud service to extract document text,
    supporting page- and block-level extraction.

    Attributes
    ----------
    supported_levels : list of str
        The supported extraction levels: `page`, `block`.
    client : LlamaParse
        The LlamaParse client instance.
    """

    # supported_levels: list[str] = ["page", "block"]

    def _initialize_driver(self):
        """Initialize the Llama Parse driver.

        Raises
        ------
        ImportError
            If LlamaParse dependencies are not installed
        """
        try:
            from llama_cloud_services import LlamaParse
        except ImportError as e:
            raise ImportError(
                'LlamaParse dependencies not installed. '
                "Install with 'pip install parxy-core[llama]'"
            ) from e

        self.__client = LlamaParse(**self._config)

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'block',
        **kwargs,
    ) -> Document:
        """Parse a document using LlamaParse.

        Parameters
        ----
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Must be one of `supported_levels`. Default is `"block"`.
        raw : bool, optional
            If True, return the raw `JobResult` object from LlamaParse instead of a `Document`. Default is False.

        Returns
        -------
        Document
            A parsed `Document` in unified format.

        Raises
        ------
        ImportError
            If LlamaParse dependencies are not installed
        AuthenticationException
            If authentication with LlamaParse fails
        FileNotFoundException
            If the input file cannot be accessed
        ParsingException
            If any other parsing error occurs
        """

        extra_info = None
        if isinstance(file, (io.BytesIO, bytes)):
            extra_info = {'file_name': 'file-name'}

        try:
            res = self.__client.parse(file, extra_info=extra_info)
        except FileNotFoundError as fex:
            raise FileNotFoundException(fex, self.__class__) from fex
        except Exception as ex:
            # Handle HTTP status errors specifically for authentication failures
            if hasattr(ex, '__cause__') and ex.__cause__ is not None:
                cause = ex.__cause__
                if hasattr(cause, 'response') and cause.response is not None:
                    status_code = cause.response.status_code
                    error_detail = (
                        cause.response.json() if hasattr(cause.response, 'json') else {}
                    )

                    if status_code in (401, 403):
                        raise AuthenticationException(
                            message=str(
                                error_detail.get('detail', 'Authentication failed')
                            ),
                            service=self.__class__,
                            details={
                                'status_code': status_code,
                                'error_response': error_detail,
                            },
                        ) from ex

            # For all other errors, raise as parsing exception
            raise ParsingException(str(ex), self.__class__) from ex

        if res.error is not None:
            raise ParsingException(
                res.error, self.__class__, res.model_dump(exclude={'file_name'})
            )

        return llamaparse_to_parxy(doc=res, level=level)


def llamaparse_to_parxy(
    doc: JobResult,
    level: str,
) -> Document:
    """Convert a LlamaParse `JobResult` to a `Document` object.

    Parameters
    ----
    doc : JobResult
        The LlamaParse result object.
    level : str
        Desired extraction level.

    Returns
    -------
    Document
        The converted `Document` in unified format.
    """
    pages = [_convert_page(page, level.upper()) for page in doc.pages]
    return Document(
        filename=doc.file_name,
        pages=pages,
        source_data=doc.model_dump(exclude={'file_name', 'pages'}),
    )


def _convert_text_block(text_block: PageItem, page_number: int) -> TextBlock:
    """Convert a LlamaParse `PageItem` to a `TextBlock`.

    Parameters
    ----
    text_block : PageItem
        The LlamaParse page item.
    page_number : int
        The page number (0-based).

    Returns
    -------
    TextBlock
        The converted `TextBlock` object.
    """
    bbox = BoundingBox(
        x0=text_block.bBox.x,
        y0=text_block.bBox.y,
        x1=text_block.bBox.x + text_block.bBox.w,
        y1=text_block.bBox.y + text_block.bBox.h,
    )
    return TextBlock(
        type='text',
        category=text_block.type,
        level=text_block.lvl,
        text=text_block.value if text_block.value else '',
        bbox=bbox,
        page=page_number,
        source_data=text_block.model_dump(exclude={'bBox', 'value', 'type', 'lvl'}),
    )


def _convert_page(
    page: LlamaPage,
    level: str,
) -> Page:
    """Convert a LlamaParse `Page` to a `Page` object.

    Parameters
    ----
    page : LlamaPage
        The LlamaParse page object.
    level : str
        Desired extraction level.

    Returns
    -------
    Page
        The converted `Page` object.
    """
    text_blocks = None
    if HierarchyLevel[level] >= HierarchyLevel.BLOCK:
        text_blocks = [_convert_text_block(item, page.page - 1) for item in page.items]
    return Page(
        number=page.page - 1,
        width=page.width,
        height=page.height,
        text=page.text,
        blocks=text_blocks,
        source_data=page.model_dump(
            exclude={'page', 'text', 'items', 'width', 'height'}
        ),
    )

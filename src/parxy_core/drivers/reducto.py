import io
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from parxy_core.models.config import ReductoConfig
from parxy_core.tracing.utils import trace_with_output

if TYPE_CHECKING:
    from reducto import Reducto
    from reducto.types.shared.parse_response import (
        ResultFullResult,
        ResultFullResultChunkBlock,
    )
else:
    Reducto = None
    ResultFullResult = object
    ResultFullResultChunkBlock = object

from parxy_core.drivers import Driver
from parxy_core.models import (
    Document,
    Page,
    BoundingBox,
    TextBlock,
    TableBlock,
    ImageBlock,
    HierarchyLevel,
)
from parxy_core.exceptions import (
    ParsingException,
    AuthenticationException,
    FileNotFoundException,
)

# Mapping from Reducto block types to WAI-ARIA document structure roles.
REDUCTO_TO_ROLE: dict[str, str] = {
    'Header': 'doc-pageheader',
    'Footer': 'doc-pagefooter',
    'Title': 'doc-title',
    'Section Header': 'heading',
    'Page Number': 'doc-pagefooter',
    'List Item': 'list',
    'Figure': 'figure',
    'Table': 'table',
    'Key Value': 'generic',
    'Text': 'paragraph',
    'Comment': 'generic',
    'Signature': 'generic',
}

# Options that can be overridden per-call via kwargs
_PER_CALL_OPTIONS = frozenset(
    {
        'extraction_mode',
        'table_output_format',
        'page_range',
        'summarize_figures',
    }
)


class ReductoDriver(Driver):
    """Reducto document processing via the Reducto Parse API.

    Attributes
    ----------
    supported_levels : list of str
        The supported extraction levels: `page`, `block`.
    """

    supported_levels = ['page', 'block']

    _config: ReductoConfig

    def _initialize_driver(self):
        try:
            from reducto import Reducto as ReductoClient

            self._ReductoClient = ReductoClient
        except ImportError as e:
            raise ImportError(
                'Reducto dependencies not installed. '
                "Install with 'pip install reductoai'"
            ) from e

    def _create_client(self) -> 'Reducto':
        kwargs: dict = {}
        if self._config and self._config.api_key:
            kwargs['api_key'] = self._config.api_key.get_secret_value()
        if self._config and self._config.environment:
            kwargs['environment'] = self._config.environment
        if self._config and self._config.base_url:
            kwargs['base_url'] = self._config.base_url
        if self._config and self._config.timeout:
            kwargs['timeout'] = self._config.timeout
        return self._ReductoClient(**kwargs)

    def _get_opt(self, overrides: dict, key: str, default=None):
        """Return the value for ``key`` from overrides, config, or default."""
        if key in overrides:
            return overrides[key]
        if self._config and hasattr(self._config, key):
            val = getattr(self._config, key)
            if val is not None:
                return val
        return default

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'block',
        **kwargs,
    ) -> Document:
        """Parse a document using the Reducto Parse API.

        Parameters
        -------
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Must be one of `supported_levels`. Default is `"block"`.
        **kwargs
            Per-call configuration overrides. Supported options:

            - extraction_mode: Text extraction mode ('ocr' or 'hybrid')
            - table_output_format: Table format ('html', 'json', 'md', 'csv', 'dynamic')
            - page_range: Page range to process (e.g. {'start': 1, 'end': 5})
            - summarize_figures: If True, summarize figures using a vision model

        Returns
        -------
        Document
            A parsed `Document` in unified format.

        Raises
        ------
        ImportError
            If reductoai is not installed
        AuthenticationException
            If authentication with Reducto fails
        FileNotFoundException
            If the input file cannot be accessed
        ParsingException
            If any other parsing error occurs
        """
        overrides = {k: v for k, v in kwargs.items() if k in _PER_CALL_OPTIONS}
        client = self._create_client()

        try:
            from reducto._exceptions import AuthenticationError, PermissionDeniedError
        except ImportError:
            AuthenticationError = Exception  # type: ignore[assignment,misc]
            PermissionDeniedError = Exception  # type: ignore[assignment,misc]

        try:
            filename, stream = self.handle_file_input(file)
            upload_filename = Path(filename).name if filename else 'document.pdf'

            upload = client.upload(file=(upload_filename, stream))
            upload_file_id = upload.file_id
            input_url = f'reducto://{upload_file_id}'

            with self._trace_parse(filename, stream, **kwargs) as span:
                parse_kwargs: dict = {'input': input_url}

                settings: dict = {}
                extraction_mode = self._get_opt(overrides, 'extraction_mode', None)
                if extraction_mode:
                    settings['extraction_mode'] = extraction_mode
                page_range = self._get_opt(overrides, 'page_range', None)
                if page_range:
                    settings['page_range'] = page_range
                if settings:
                    parse_kwargs['settings'] = settings

                formatting: dict = {}
                table_output_format = self._get_opt(
                    overrides, 'table_output_format', None
                )
                if table_output_format:
                    formatting['table_output_format'] = table_output_format
                if formatting:
                    parse_kwargs['formatting'] = formatting

                enhance: dict = {}
                summarize_figures = self._get_opt(overrides, 'summarize_figures', None)
                if summarize_figures is not None:
                    enhance['summarize_figures'] = summarize_figures
                if enhance:
                    parse_kwargs['enhance'] = enhance

                response = client.parse.run(**parse_kwargs)

                from reducto.lib.helpers import handle_url_response

                full_response = handle_url_response(response)

                span.set_attribute('output.document', full_response.model_dump_json())

        except FileNotFoundError as fex:
            raise FileNotFoundException(fex, self.__class__) from fex
        except (AuthenticationError, PermissionDeniedError) as ex:
            raise AuthenticationException(
                message=str(ex),
                service=self.__class__.__name__,
                details={
                    'status_code': getattr(ex, 'status_code', None),
                    'error_response': getattr(ex, 'body', None),
                },
            ) from ex
        except Exception as ex:
            raise ParsingException(str(ex), self.__class__) from ex

        converted_document = reducto_to_parxy(
            result=full_response.result,
            filename=filename,
            level=level,
        )

        if converted_document.parsing_metadata is None:
            converted_document.parsing_metadata = {}

        converted_document.parsing_metadata['job_id'] = full_response.job_id
        converted_document.parsing_metadata['upload_file_id'] = upload_file_id
        converted_document.parsing_metadata['duration'] = full_response.duration
        converted_document.parsing_metadata['num_pages'] = full_response.usage.num_pages
        if full_response.usage.credits is not None:
            converted_document.parsing_metadata['cost_estimation'] = (
                full_response.usage.credits
            )
            converted_document.parsing_metadata['cost_estimation_unit'] = 'credits'
        if full_response.pdf_url:
            converted_document.parsing_metadata['pdf_url'] = full_response.pdf_url

        return converted_document


@trace_with_output('converting')
def reducto_to_parxy(
    result: 'ResultFullResult',
    filename: str,
    level: str,
) -> Document:
    """Convert a Reducto ``ResultFullResult`` to a ``Document`` object.

    Parameters
    ----------
    result : ResultFullResult
        The Reducto parse result.
    filename : str
        Original filename.
    level : str
        Desired extraction level.

    Returns
    -------
    Document
        The converted ``Document`` in unified format.
    """
    blocks_by_page: dict[int, list] = {}

    for chunk in result.chunks:
        for block in chunk.blocks:
            page_num = block.bbox.page
            if page_num not in blocks_by_page:
                blocks_by_page[page_num] = []
            blocks_by_page[page_num].append(block)

    include_blocks = HierarchyLevel[level.upper()] >= HierarchyLevel.BLOCK

    pages = []
    for page_num in sorted(blocks_by_page.keys()):
        raw_blocks = blocks_by_page[page_num]
        page_text = '\n'.join(b.content for b in raw_blocks if b.content)

        page_blocks = None
        if include_blocks:
            page_blocks = []
            for raw_block in raw_blocks:
                if raw_block.type == 'Table':
                    page_blocks.append(_convert_table_block(raw_block, page_num))
                elif raw_block.type == 'Figure':
                    page_blocks.append(_convert_image_block(raw_block, page_num))
                else:
                    page_blocks.append(_convert_text_block(raw_block, page_num))

        pages.append(
            Page(
                number=page_num,
                text=page_text,
                blocks=page_blocks,
            )
        )

    return Document(
        filename=filename,
        pages=pages,
    )


def _convert_bbox(bbox) -> Optional[BoundingBox]:
    if bbox is None:
        return None
    return BoundingBox(
        x0=bbox.left,
        y0=bbox.top,
        x1=bbox.left + bbox.width,
        y1=bbox.top + bbox.height,
    )


def _convert_text_block(
    block: 'ResultFullResultChunkBlock', page_number: int
) -> TextBlock:
    bbox = _convert_bbox(block.bbox)
    role = REDUCTO_TO_ROLE.get(block.type, 'generic')

    source_data: dict = {}
    if hasattr(block, 'model_dump'):
        source_data = block.model_dump(exclude={'content', 'type', 'bbox'})

    return TextBlock(
        type='text',
        role=role,
        category=block.type,
        text=block.content,
        bbox=bbox,
        page=page_number,
        source_data=source_data,
    )


def _convert_table_block(
    block: 'ResultFullResultChunkBlock', page_number: int
) -> TableBlock:
    bbox = _convert_bbox(block.bbox)

    source_data: dict = {}
    if hasattr(block, 'model_dump'):
        source_data = block.model_dump(exclude={'content', 'type', 'bbox'})

    return TableBlock(
        type='table',
        role='table',
        category=block.type,
        text=block.content,
        bbox=bbox,
        page=page_number,
        source_data=source_data,
    )


def _convert_image_block(
    block: 'ResultFullResultChunkBlock', page_number: int
) -> ImageBlock:
    bbox = _convert_bbox(block.bbox)
    image_url = getattr(block, 'image_url', None)

    source_data: dict = {}
    if hasattr(block, 'model_dump'):
        source_data = block.model_dump(exclude={'content', 'type', 'bbox'})

    return ImageBlock(
        type='image',
        role='figure',
        category=block.type,
        name=image_url,
        alt_text=block.content or None,
        bbox=bbox,
        page=page_number,
        source_data=source_data,
    )

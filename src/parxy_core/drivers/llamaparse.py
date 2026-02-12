import io
from typing import TYPE_CHECKING, Optional

import requests

from parxy_core.models.config import LlamaParseConfig
from parxy_core.tracing.utils import trace_with_output

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
from parxy_core.models import (
    Document,
    Page,
    BoundingBox,
    TextBlock,
    TableBlock,
    ImageBlock,
    HierarchyLevel,
)
from parxy_core.utils import safe_json_dumps
from parxy_core.exceptions import (
    ParsingException,
    AuthenticationException,
    FileNotFoundException,
)

# Mapping from LlamaParse types to WAI-ARIA document structure roles
# See docs/explanation/document-roles.md for role definitions
LLAMAPARSE_TO_ROLE: dict[str, str] = {
    'text': 'paragraph',
    'table': 'table',
    'tables': 'table',
    'figure': 'figure',
    'figures': 'figure',
    'list': 'list',
    'lists': 'list',
    # Footer variants
    'footer': 'doc-pagefooter',
    'page-footer': 'doc-pagefooter',
    'page_footer': 'doc-pagefooter',
    'page-number': 'doc-pagefooter',
    # Footnote variants
    'footnote': 'doc-footnote',
    'note': 'doc-footnote',
    'endnote': 'doc-endnotes',
    'annotation': 'doc-footnote',
    'footer-note': 'doc-footnote',
    # Heading variants
    'heading': 'heading',
    'title': 'doc-title',
    'titles': 'heading',
    'subtitle': 'doc-subtitle',
    'section': 'heading',
    'chapter': 'doc-chapter',
    # Header variants
    'page-header': 'doc-pageheader',
    'page_header': 'doc-pageheader',
    'page-heading': 'doc-pageheader',
    'header': 'doc-pageheader',
}

_credits_per_parsing_mode = {
    # Minimum credits per parsing mode as deduced from https://developers.llamaindex.ai/python/cloud/general/pricing/
    'accurate': 3,  # equivalent to Parse page with LLM as observed in their dashboard
    'parse_page_without_llm': 1,
    'parse_page_with_llm': 3,
    'parse_page_with_lvm': 6,
    'parse_page_with_agent': 10,
    'parse_document_with_llm': 30,
    'parse_document_with_agent': 30,
}

# Options that can be overridden per-call via kwargs
_PER_CALL_OPTIONS = frozenset(
    {
        'model',
        'skip_diagonal_text',
        'preset',
        'parse_mode',
        'language',
        'target_pages',
        'max_pages',
        'continuous_mode',
        'disable_ocr',
        'disable_image_extraction',
        'fast_mode',
        'premium_mode',
        'high_res_ocr',
        'extract_layout',
        'auto_mode',
        'do_not_unroll_columns',
    }
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

    _config: LlamaParseConfig

    # supported_levels: list[str] = ["page", "block"]

    def _initialize_driver(self):
        """Initialize the Llama Parse driver.

        Validates that dependencies are installed and creates the default client.
        Client creation is also available per-call to support configuration overrides.

        Raises
        ------
        ImportError
            If LlamaParse dependencies are not installed
        """
        try:
            from llama_cloud_services import LlamaParse

            self._LlamaParse = LlamaParse  # Store class reference for per-call clients
        except ImportError as e:
            raise ImportError(
                'LlamaParse dependencies not installed. '
                "Install with 'pip install parxy[llama]'"
            ) from e

        # Create default client for calls without overrides
        self.__default_client = self._create_client(
            self._config.model_dump() if self._config else {},
            api_key=self._config.api_key if self._config else None,
        )

    def _create_client(
        self, config_dict: dict, api_key: Optional['SecretStr'] = None
    ) -> 'LlamaParse':
        """Create a LlamaParse client with the given configuration.

        Parameters
        ----------
        config_dict : dict
            Configuration dictionary to pass to LlamaParse constructor.
        api_key : SecretStr, optional
            The API key (passed separately since it's excluded from model_dump).

        Returns
        -------
        LlamaParse
            Configured client instance
        """
        # Make a copy to avoid modifying the original
        config = config_dict.copy()

        # Handle api_key (may be SecretStr, needs to be converted)
        if api_key is not None:
            if hasattr(api_key, 'get_secret_value'):
                api_key = api_key.get_secret_value()
            # Only pass api_key if it has a value, otherwise let LlamaParse use default
            config['api_key'] = api_key

        return self._LlamaParse(**config)

    def _fetch_usage_metrics(self, job_id: str) -> Optional[dict]:
        """Fetch actual usage metrics from the LlamaParse beta API.

        Parameters
        ----------
        job_id : str
            The job ID to fetch metrics for

        Returns
        -------
        Optional[dict]
            Dictionary with 'total_cost', 'cost_unit', 'parsing_mode_counts', and 'mode_details'
            Returns None if organization_id is not configured or if the API call fails
        """
        # Only fetch if organization_id is configured
        if not self._config or not self._config.organization_id:
            return None

        try:
            # Construct the beta API endpoint
            base_url = self._config.base_url.rstrip('/')
            endpoint = f'{base_url}/api/v1/beta/usage-metrics'

            # Prepare request parameters
            params = {
                'organization_id': self._config.organization_id,
                'event_aggregation_key': job_id,
            }

            # Prepare headers with authentication
            headers = {
                'Authorization': f'Bearer {self._config.api_key.get_secret_value()}',
                'Content-Type': 'application/json',
            }

            # Make the API request
            response = requests.get(
                endpoint, params=params, headers=headers, timeout=10
            )
            response.raise_for_status()

            data = response.json()
            items = data.get('items', [])

            if not items:
                return None

            # Aggregate usage data by parsing mode
            parsing_mode_counts = {}
            mode_details = []

            for item in items:
                if item.get('event_type') == 'pages_parsed':
                    mode = item.get('properties', {}).get('mode', 'unknown')
                    pages = item.get('value', 0)
                    model = item.get('properties', {}).get('model', 'unknown')

                    # Count pages per mode
                    parsing_mode_counts[mode] = parsing_mode_counts.get(mode, 0) + pages

                    # Store detailed info
                    mode_details.append(
                        {
                            'mode': mode,
                            'model': model,
                            'pages': pages,
                            'day': item.get('day'),
                        }
                    )

            # Calculate total cost based on actual usage
            total_cost = 0
            for mode, count in parsing_mode_counts.items():
                credits_per_page = _credits_per_parsing_mode.get(mode, 3)
                total_cost += credits_per_page * count

            return {
                'total_cost': total_cost,
                'cost_unit': 'credits',
                'parsing_mode_counts': parsing_mode_counts,
                'mode_details': mode_details,
            }

        except Exception as e:
            # Log the error but don't fail the parsing
            self._logger.warning(
                f'Failed to fetch usage metrics from beta API: {str(e)}'
            )
            return None

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'block',
        **kwargs,
    ) -> Document:
        """Parse a document using LlamaParse.

        Parameters
        -------
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Must be one of `supported_levels`. Default is `"block"`.
        **kwargs
            Per-call configuration overrides. Supported options:

            - model: Document model name for parse_with_agent
            - skip_diagonal_text: Skip diagonal text (useful for CAD)
            - preset: Parser preset (overrides most options)
            - parse_mode: Parsing mode ('accurate', 'parse_page_with_llm', etc.)
            - language: Text language
            - target_pages: Specific pages to parse (e.g., '0,2,5-10')
            - max_pages: Maximum pages to extract
            - continuous_mode: Better table handling across pages
            - disable_ocr: Disable OCR
            - disable_image_extraction: Don't extract images
            - fast_mode: Speed over accuracy
            - premium_mode: Best parser mode
            - high_res_ocr: High resolution OCR
            - extract_layout: Extract layout information
            - auto_mode: Automatic mode selection
            - do_not_unroll_columns: Keep columns in layout

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
        # Extract per-call overrides from kwargs
        overrides = {k: v for k, v in kwargs.items() if k in _PER_CALL_OPTIONS}
        remaining_kwargs = {
            k: v for k, v in kwargs.items() if k not in _PER_CALL_OPTIONS
        }

        # Determine which client to use
        if overrides:
            # Merge base config with overrides
            merged_config = self._config.model_dump() if self._config else {}
            merged_config.update(overrides)
            client = self._create_client(
                merged_config,
                api_key=self._config.api_key if self._config else None,
            )
        else:
            client = self.__default_client

        try:
            filename, stream = self.handle_file_input(file)
            extra_info = {'file_name': filename if len(filename) > 0 else 'default'}
            with self._trace_parse(filename, stream, **kwargs) as span:
                res = client.parse(stream, extra_info=extra_info)
                span.set_attribute('output.document', safe_json_dumps(res.model_dump()))
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

        converted_document = llamaparse_to_parxy(doc=res, level=level)

        if converted_document.parsing_metadata is None:
            converted_document.parsing_metadata = {}

        converted_document.parsing_metadata['job_id'] = res.job_id
        converted_document.parsing_metadata['job_metadata'] = (
            res.job_metadata.model_dump_json()
        )
        converted_document.parsing_metadata['job_error'] = getattr(res, 'error', None)
        converted_document.parsing_metadata['job_error_code'] = getattr(
            res, 'error_code', None
        )
        converted_document.parsing_metadata['job_status'] = getattr(res, 'status', None)

        # Try to fetch actual usage metrics from beta API if organization_id is configured
        usage_metrics = self._fetch_usage_metrics(res.job_id)

        if usage_metrics:
            # Use actual metrics from the API
            converted_document.parsing_metadata['cost_estimation'] = usage_metrics[
                'total_cost'
            ]
            converted_document.parsing_metadata['cost_estimation_unit'] = usage_metrics[
                'cost_unit'
            ]
            converted_document.parsing_metadata['parsing_mode_counts'] = usage_metrics[
                'parsing_mode_counts'
            ]
            converted_document.parsing_metadata['cost_data_source'] = 'beta_api'
            converted_document.parsing_metadata['usage_details'] = usage_metrics[
                'mode_details'
            ]
        else:
            # Fall back to estimation from page source_data
            parsing_modes = {}
            parsing_mode_counts = {}

            for page in converted_document.pages:
                if page.source_data and 'parsingMode' in page.source_data:
                    mode = page.source_data['parsingMode']
                    parsing_modes[page.number] = mode

                    # Count pages per parsing mode
                    if mode in parsing_mode_counts:
                        parsing_mode_counts[mode] += 1
                    else:
                        parsing_mode_counts[mode] = 1

            if parsing_modes:
                converted_document.parsing_metadata['page_parsing_modes'] = (
                    parsing_modes
                )
                converted_document.parsing_metadata['parsing_mode_counts'] = (
                    parsing_mode_counts
                )

                # Calculate cost estimation based on parsing modes
                total_cost = 0
                for mode, count in parsing_mode_counts.items():
                    # Use the credit cost from the dictionary, or default to 3 if not recognized
                    credits_per_page = _credits_per_parsing_mode.get(mode, 3)
                    total_cost += credits_per_page * count

                converted_document.parsing_metadata['cost_estimation'] = total_cost
                converted_document.parsing_metadata['cost_estimation_unit'] = 'credits'
                converted_document.parsing_metadata['cost_data_source'] = 'estimation'

        return converted_document


@trace_with_output('converting')
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
    # Handle empty page marker
    text_value = text_block.value if text_block.value else ''
    if text_value == 'NO_CONTENT_HERE':
        text_value = ''
    category = text_block.type
    role = LLAMAPARSE_TO_ROLE.get(category, 'generic') if category else 'generic'
    return TextBlock(
        type='text',
        role=role,
        category=category,
        level=text_block.lvl,
        text=text_value,
        bbox=bbox,
        page=page_number,
        source_data=text_block.model_dump(exclude={'bBox', 'value', 'type', 'lvl'}),
    )


def _convert_table_block(text_block: PageItem, page_number: int) -> TableBlock:
    """Convert a LlamaParse `PageItem` with table type to a `TableBlock`.

    Parameters
    ----
    text_block : PageItem
        The LlamaParse page item containing table data.
    page_number : int
        The page number (0-based).

    Returns
    -------
    TableBlock
        The converted `TableBlock` object with markdown table content.
    """
    bbox = BoundingBox(
        x0=text_block.bBox.x,
        y0=text_block.bBox.y,
        x1=text_block.bBox.x + text_block.bBox.w,
        y1=text_block.bBox.y + text_block.bBox.h,
    )
    # Use markdown representation as the text content for tables
    text_value = getattr(text_block, 'md', '') or ''
    category = text_block.type
    role = LLAMAPARSE_TO_ROLE.get(category, 'table') if category else 'table'
    return TableBlock(
        type='table',
        role=role,
        category=category,
        text=text_value,
        bbox=bbox,
        page=page_number,
        source_data=text_block.model_dump(exclude={'bBox', 'value', 'type', 'lvl'}),
    )


def _convert_image_block(image_data, page_number: int) -> ImageBlock:
    """Convert a LlamaParse image entry to an `ImageBlock`.

    Parameters
    ----
    image_data
        Image data from the LlamaParse page (model object or dict).
    page_number : int
        The page number (0-based).

    Returns
    -------
    ImageBlock
        The converted `ImageBlock` object.
    """
    # Normalise to dict so we can handle both Pydantic models and plain dicts
    if isinstance(image_data, dict):
        img = image_data
    elif hasattr(image_data, 'model_dump'):
        img = image_data.model_dump()
    else:
        img = vars(image_data)

    bbox = BoundingBox(
        x0=img.get('x', 0),
        y0=img.get('y', 0),
        x1=img.get('x', 0) + img.get('width', 0),
        y1=img.get('y', 0) + img.get('height', 0),
    )

    # Build alt_text from OCR entries when available
    ocr_entries = img.get('ocr') or []
    alt_text = (
        ' '.join(
            entry.get('text', '')
            if isinstance(entry, dict)
            else getattr(entry, 'text', '')
            for entry in ocr_entries
        ).strip()
        or None
    )

    return ImageBlock(
        type='image',
        role='figure',
        category='figure',
        name=img.get('name'),
        alt_text=alt_text,
        bbox=bbox,
        page=page_number,
        source_data=img,
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
    blocks = None
    if HierarchyLevel[level] >= HierarchyLevel.BLOCK:
        blocks = []
        for item in page.items:
            if item.type in ('table', 'tables'):
                blocks.append(_convert_table_block(item, page.page))
            else:
                blocks.append(_convert_text_block(item, page.page))

        # Process page-level images into ImageBlocks
        images = getattr(page, 'images', None) or []
        for image_data in images:
            blocks.append(_convert_image_block(image_data, page.page))
    return Page(
        number=page.page,
        width=page.width,
        height=page.height,
        text=page.text if page.text != 'NO_CONTENT_HERE' else '',
        blocks=blocks,
        source_data=page.model_dump(
            exclude={'page', 'text', 'items', 'width', 'height'}
        ),
    )

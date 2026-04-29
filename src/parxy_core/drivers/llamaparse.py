import io
from typing import TYPE_CHECKING, Optional

import requests

from parxy_core.models.config import LlamaParseConfig
from parxy_core.tracing.utils import trace_with_output

if TYPE_CHECKING:
    from llama_cloud import LlamaCloud
    from llama_cloud.types.parsing_get_response import (
        ParsingGetResponse,
        ItemsPageStructuredResultPage,
        MetadataPage,
    )
else:
    LlamaCloud = None
    ParsingGetResponse = object
    ItemsPageStructuredResultPage = object
    MetadataPage = object

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

# Mapping from LlamaParse v2 item types to WAI-ARIA document structure roles.
# See docs/explanation/document-roles.md for role definitions.
LLAMAPARSE_TO_ROLE: dict[str, str] = {
    # New API v2 item types
    'text': 'paragraph',
    'heading': 'heading',
    'table': 'table',
    'image': 'figure',
    'list': 'list',
    'code': 'generic',
    'link': 'generic',
    'header': 'doc-pageheader',
    'footer': 'doc-pagefooter',
    # Legacy types retained for compatibility with stored source_data
    'tables': 'table',
    'figure': 'figure',
    'figures': 'figure',
    'lists': 'list',
    'page-footer': 'doc-pagefooter',
    'page_footer': 'doc-pagefooter',
    'page-number': 'doc-pagefooter',
    'footnote': 'doc-footnote',
    'note': 'doc-footnote',
    'endnote': 'doc-endnotes',
    'annotation': 'doc-footnote',
    'footer-note': 'doc-footnote',
    'title': 'doc-title',
    'titles': 'heading',
    'subtitle': 'doc-subtitle',
    'section': 'heading',
    'chapter': 'doc-chapter',
    'page-header': 'doc-pageheader',
    'page_header': 'doc-pageheader',
    'page-heading': 'doc-pageheader',
}

# Legacy parse_mode values (llama_cloud_services API) mapped to new tier names.
_PARSE_MODE_TO_TIER: dict[str, str] = {
    'parse_page_without_llm': 'fast',
    'parse_page_with_llm': 'cost_effective',
    'accurate': 'cost_effective',
    'parse_page_with_lvm': 'agentic',
    'parse_page_with_agent': 'agentic',
    'parse_document_with_llm': 'agentic',
    'parse_document_with_agent': 'agentic_plus',
}

# Estimated credits per page per tier (for cost fallback estimation).
_credits_per_tier: dict[str, int] = {
    'fast': 1,
    'cost_effective': 3,
    'agentic': 6,
    'agentic_plus': 10,
}

# Options that can be overridden per-call via kwargs
_PER_CALL_OPTIONS = frozenset({
    # New API v2 options
    'tier',
    'version',
    # Legacy options mapped to new API
    'parse_mode',
    'premium_mode',
    'fast_mode',
    'language',
    'target_pages',
    'max_pages',
    'skip_diagonal_text',
    'do_not_unroll_columns',
    'disable_image_extraction',
    'disable_ocr',
    'continuous_mode',
    'do_not_cache',
})


class LlamaParseDriver(Driver):
    """LlamaCloud document processing via LlamaParse API v2.

    Attributes
    ----------
    supported_levels : list of str
        The supported extraction levels: `page`, `block`.
    client : LlamaCloud
        The LlamaCloud client instance (created fresh per call).
    """

    _config: LlamaParseConfig

    def _initialize_driver(self):
        """Initialize the LlamaParse driver.

        Validates that the llama-cloud package is installed. A fresh client is
        created per ``_handle`` call to avoid sharing state across threads.

        Raises
        ------
        ImportError
            If llama-cloud dependencies are not installed
        """
        try:
            from llama_cloud import LlamaCloud

            self._LlamaCloud = LlamaCloud
        except ImportError as e:
            raise ImportError(
                'LlamaParse dependencies not installed. '
                "Install with 'pip install parxy[llama]'"
            ) from e

    def _create_client(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> 'LlamaCloud':
        """Create a LlamaCloud client."""
        kwargs: dict = {}
        if api_key:
            kwargs['api_key'] = api_key
        if base_url:
            kwargs['base_url'] = base_url
        return self._LlamaCloud(**kwargs)

    def _resolve_tier(self, overrides: dict) -> str:
        """Resolve the parsing tier, honouring legacy config options."""
        if overrides.get('tier'):
            return overrides['tier']
        if overrides.get('premium_mode') or (self._config and self._config.premium_mode):
            return 'agentic_plus'
        if overrides.get('fast_mode') or (self._config and self._config.fast_mode):
            return 'fast'
        parse_mode = overrides.get('parse_mode') or (
            self._config.parse_mode if self._config else None
        )
        if parse_mode:
            return _PARSE_MODE_TO_TIER.get(parse_mode, 'cost_effective')
        if self._config and self._config.tier:
            return self._config.tier
        return 'cost_effective'

    def _get_opt(self, overrides: dict, key: str, default=None):
        """Return the value for ``key`` from overrides, config, or default."""
        if key in overrides:
            return overrides[key]
        if self._config and hasattr(self._config, key):
            val = getattr(self._config, key)
            if val is not None:
                return val
        return default

    def _build_processing_options(self, overrides: dict) -> dict:
        opts: dict = {}
        ignore_opts: dict = {}

        if self._get_opt(overrides, 'skip_diagonal_text', False):
            ignore_opts['ignore_diagonal_text'] = True
        if self._get_opt(overrides, 'disable_ocr', False):
            ignore_opts['ignore_text_in_image'] = True
        if ignore_opts:
            opts['ignore'] = ignore_opts

        language = self._get_opt(overrides, 'language', None)
        if language:
            opts['ocr_parameters'] = {'languages': [language]}

        return opts

    def _build_output_options(self, overrides: dict) -> dict:
        opts: dict = {}

        if self._get_opt(overrides, 'do_not_unroll_columns', False):
            opts['spatial_text'] = {'do_not_unroll_columns': True}

        if self._get_opt(overrides, 'continuous_mode', False):
            opts['markdown'] = {'tables': {'merge_continued_tables': True}}

        if self._get_opt(overrides, 'disable_image_extraction', False):
            opts['images_to_save'] = []

        return opts

    def _build_page_ranges(self, overrides: dict) -> dict:
        opts: dict = {}
        target_pages = self._get_opt(overrides, 'target_pages', None)
        if target_pages:
            opts['target_pages'] = target_pages
        max_pages = self._get_opt(overrides, 'max_pages', None)
        if max_pages:
            opts['max_pages'] = max_pages
        return opts

    def _fetch_usage_metrics(self, job_id: str) -> Optional[dict]:
        """Fetch actual usage metrics from the LlamaParse beta API.

        Parameters
        ----------
        job_id : str
            The job ID to fetch metrics for

        Returns
        -------
        Optional[dict]
            Dictionary with cost and mode data, or None if unavailable.
        """
        if not self._config or not self._config.organization_id:
            return None

        try:
            base_url = self._config.base_url.rstrip('/')
            endpoint = f'{base_url}/api/v1/beta/usage-metrics'

            params = {
                'organization_id': self._config.organization_id,
                'event_aggregation_key': job_id,
            }

            headers = {
                'Authorization': f'Bearer {self._config.api_key.get_secret_value()}',
                'Content-Type': 'application/json',
            }

            response = requests.get(endpoint, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            items = data.get('items', [])

            if not items:
                return None

            parsing_mode_counts: dict = {}
            mode_details = []

            for item in items:
                if item.get('event_type') == 'pages_parsed':
                    mode = item.get('properties', {}).get('mode', 'unknown')
                    pages = item.get('value', 0)
                    model = item.get('properties', {}).get('model', 'unknown')

                    parsing_mode_counts[mode] = parsing_mode_counts.get(mode, 0) + pages
                    mode_details.append({
                        'mode': mode,
                        'model': model,
                        'pages': pages,
                        'day': item.get('day'),
                    })

            total_cost = sum(
                _credits_per_tier.get(mode, 3) * count
                for mode, count in parsing_mode_counts.items()
            )

            return {
                'total_cost': total_cost,
                'cost_unit': 'credits',
                'parsing_mode_counts': parsing_mode_counts,
                'mode_details': mode_details,
            }

        except Exception as e:
            self._logger.warning(f'Failed to fetch usage metrics from beta API: {str(e)}')
            return None

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'block',
        **kwargs,
    ) -> Document:
        """Parse a document using LlamaParse API v2.

        Parameters
        -------
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Must be one of `supported_levels`. Default is `"block"`.
        **kwargs
            Per-call configuration overrides. Supported options:

            - tier: Parsing tier ('fast', 'cost_effective', 'agentic', 'agentic_plus')
            - version: API version string (default 'latest')
            - parse_mode: Legacy mode name (mapped to tier for backward compatibility)
            - premium_mode: If True, uses 'agentic_plus' tier
            - fast_mode: If True, uses 'fast' tier
            - language: OCR language code (e.g. 'en')
            - target_pages: Comma-separated 1-based page numbers or ranges (e.g. '1,3,5-8')
            - max_pages: Maximum pages to extract
            - skip_diagonal_text: Skip text rotated at an angle
            - do_not_unroll_columns: Keep multi-column layout intact
            - disable_image_extraction: Skip image extraction
            - disable_ocr: Disable OCR on images
            - continuous_mode: Merge tables that span multiple pages
            - do_not_cache: Bypass result caching

        Returns
        -------
        Document
            A parsed `Document` in unified format.

        Raises
        ------
        ImportError
            If llama-cloud dependencies are not installed
        AuthenticationException
            If authentication with LlamaParse fails
        FileNotFoundException
            If the input file cannot be accessed
        ParsingException
            If any other parsing error occurs
        """
        overrides = {k: v for k, v in kwargs.items() if k in _PER_CALL_OPTIONS}

        api_key = (
            self._config.api_key.get_secret_value()
            if (self._config and self._config.api_key)
            else None
        )
        base_url = self._config.base_url if self._config else None
        client = self._create_client(api_key=api_key, base_url=base_url)

        tier = self._resolve_tier(overrides)
        version = (
            overrides.get('version')
            or (self._config.version if self._config else None)
            or 'latest'
        )

        expand = ['text', 'metadata', 'job_metadata']
        if HierarchyLevel[level.upper()] >= HierarchyLevel.BLOCK:
            expand.append('items')
            if not self._get_opt(overrides, 'disable_image_extraction', False):
                expand.append('images_content_metadata')

        processing_options = self._build_processing_options(overrides)
        output_options = self._build_output_options(overrides)
        page_ranges = self._build_page_ranges(overrides)
        disable_cache = self._get_opt(overrides, 'do_not_cache', True)

        try:
            from llama_cloud._polling import PollingError, PollingTimeoutError
            from llama_cloud._exceptions import AuthenticationError, PermissionDeniedError
        except ImportError:
            PollingError = Exception  # type: ignore[assignment,misc]
            PollingTimeoutError = Exception  # type: ignore[assignment,misc]
            AuthenticationError = Exception  # type: ignore[assignment,misc]
            PermissionDeniedError = Exception  # type: ignore[assignment,misc]

        try:
            filename, stream = self.handle_file_input(file)
            upload_filename = filename if filename else 'document.pdf'

            with self._trace_parse(filename, stream, **kwargs) as span:
                parse_kwargs: dict = {
                    'upload_file': (upload_filename, stream),
                    'tier': tier,
                    'version': version,
                    'expand': expand,
                    'disable_cache': disable_cache,
                    'verbose': self._config.verbose if self._config else False,
                }
                if self._config and self._config.organization_id:
                    parse_kwargs['organization_id'] = self._config.organization_id
                if self._config and self._config.project_id:
                    parse_kwargs['project_id'] = self._config.project_id
                if processing_options:
                    parse_kwargs['processing_options'] = processing_options
                if output_options:
                    parse_kwargs['output_options'] = output_options
                if page_ranges:
                    parse_kwargs['page_ranges'] = page_ranges

                res = client.parsing.parse(**parse_kwargs)
                span.set_attribute('output.document', res.model_dump_json())

        except FileNotFoundError as fex:
            raise FileNotFoundException(fex, self.__class__) from fex
        except (AuthenticationError, PermissionDeniedError) as ex:
            raise AuthenticationException(
                message=str(ex),
                service=self.__class__,
                details={
                    'status_code': getattr(ex, 'status_code', None),
                    'error_response': getattr(ex, 'body', None),
                },
            ) from ex
        except (PollingError, PollingTimeoutError) as ex:
            raise ParsingException(str(ex), self.__class__) from ex
        except Exception as ex:
            raise ParsingException(str(ex), self.__class__) from ex

        converted_document = llamaparse_to_parxy(doc=res, filename=filename, level=level)

        if converted_document.parsing_metadata is None:
            converted_document.parsing_metadata = {}

        converted_document.parsing_metadata['job_id'] = res.job.id
        converted_document.parsing_metadata['job_metadata'] = res.job_metadata
        converted_document.parsing_metadata['job_status'] = res.job.status
        converted_document.parsing_metadata['job_error'] = res.job.error_message
        converted_document.parsing_metadata['tier'] = tier

        usage_metrics = self._fetch_usage_metrics(res.job.id)

        if usage_metrics:
            converted_document.parsing_metadata['cost_estimation'] = usage_metrics['total_cost']
            converted_document.parsing_metadata['cost_estimation_unit'] = usage_metrics['cost_unit']
            converted_document.parsing_metadata['parsing_mode_counts'] = usage_metrics[
                'parsing_mode_counts'
            ]
            converted_document.parsing_metadata['cost_data_source'] = 'beta_api'
            converted_document.parsing_metadata['usage_details'] = usage_metrics['mode_details']
        else:
            page_count = len(converted_document.pages)
            credits_per_page = _credits_per_tier.get(tier, 3)
            converted_document.parsing_metadata['cost_estimation'] = credits_per_page * page_count
            converted_document.parsing_metadata['cost_estimation_unit'] = 'credits'
            converted_document.parsing_metadata['cost_data_source'] = 'estimation'

        return converted_document


@trace_with_output('converting')
def llamaparse_to_parxy(
    doc: 'ParsingGetResponse',
    filename: str,
    level: str,
) -> Document:
    """Convert a LlamaParse ``ParsingGetResponse`` to a ``Document`` object.

    Parameters
    ----------
    doc : ParsingGetResponse
        The LlamaParse v2 result object.
    filename : str
        Original filename (not included in the response).
    level : str
        Desired extraction level.

    Returns
    -------
    Document
        The converted ``Document`` in unified format.
    """
    metadata_by_page: dict = {}
    if doc.metadata:
        for meta_page in doc.metadata.pages:
            metadata_by_page[meta_page.page_number] = meta_page

    text_by_page: dict = {}
    if doc.text:
        for text_page in doc.text.pages:
            text_by_page[text_page.page_number] = text_page.text

    pages = []
    level_upper = level.upper()

    if doc.items:
        for items_page in doc.items.pages:
            page_text = text_by_page.get(items_page.page_number, '')
            meta_page = metadata_by_page.get(items_page.page_number)
            if getattr(items_page, 'success', True):
                page = _convert_page(items_page, page_text, meta_page, level_upper)
            else:
                page = Page(
                    number=items_page.page_number,
                    text=page_text,
                    blocks=[],
                    source_data={'error': getattr(items_page, 'error', None)},
                )
            pages.append(page)
    elif doc.text:
        for text_page in doc.text.pages:
            meta_page = metadata_by_page.get(text_page.page_number)
            source = meta_page.model_dump() if meta_page else {}
            pages.append(Page(
                number=text_page.page_number,
                text=text_page.text,
                blocks=None,
                source_data=source,
            ))

    source_data: dict = {}
    if doc.job_metadata:
        source_data['job_metadata'] = doc.job_metadata

    return Document(
        filename=filename,
        pages=pages,
        source_data=source_data,
    )


def _extract_bbox(bbox_list) -> Optional[BoundingBox]:
    """Extract the first bounding box from a list of BBox objects."""
    if not bbox_list:
        return None
    b = bbox_list[0]
    return BoundingBox(
        x0=b.x,
        y0=b.y,
        x1=b.x + b.w,
        y1=b.y + b.h,
    )


def _convert_text_block(item, page_number: int) -> TextBlock:
    """Convert a LlamaParse v2 item to a ``TextBlock``."""
    bbox = _extract_bbox(getattr(item, 'bbox', None))
    # Most items use 'value'; header/footer/list containers use 'md'
    text_value = getattr(item, 'value', None) or getattr(item, 'md', '') or ''
    if text_value == 'NO_CONTENT_HERE':
        text_value = ''
    item_type = getattr(item, 'type', None)
    role = LLAMAPARSE_TO_ROLE.get(item_type, 'generic') if item_type else 'generic'
    heading_level = getattr(item, 'level', None)

    source_data: dict = {}
    if hasattr(item, 'model_dump'):
        source_data = item.model_dump(exclude={'bbox', 'value', 'type', 'level'})

    return TextBlock(
        type='text',
        role=role,
        category=item_type,
        level=heading_level,
        text=text_value,
        bbox=bbox,
        page=page_number,
        source_data=source_data,
    )


def _convert_table_block(item, page_number: int) -> TableBlock:
    """Convert a LlamaParse v2 TableItem to a ``TableBlock``."""
    bbox = _extract_bbox(getattr(item, 'bbox', None))
    text_value = getattr(item, 'md', '') or ''
    item_type = getattr(item, 'type', 'table')
    role = LLAMAPARSE_TO_ROLE.get(item_type, 'table')

    source_data: dict = {}
    if hasattr(item, 'model_dump'):
        source_data = item.model_dump(exclude={'bbox', 'type'})

    return TableBlock(
        type='table',
        role=role,
        category=item_type,
        text=text_value,
        bbox=bbox,
        page=page_number,
        source_data=source_data,
    )


def _convert_image_block(item, page_number: int) -> ImageBlock:
    """Convert a LlamaParse v2 ImageItem to an ``ImageBlock``."""
    bbox = _extract_bbox(getattr(item, 'bbox', None))
    alt_text = getattr(item, 'caption', None) or None
    url = getattr(item, 'url', None)

    source_data: dict = {}
    if hasattr(item, 'model_dump'):
        source_data = item.model_dump(exclude={'bbox', 'type'})

    return ImageBlock(
        type='image',
        role='figure',
        category='figure',
        name=url,
        alt_text=alt_text,
        bbox=bbox,
        page=page_number,
        source_data=source_data,
    )


def _convert_page(
    items_page: 'ItemsPageStructuredResultPage',
    page_text: str,
    meta_page: Optional['MetadataPage'],
    level: str,
) -> Page:
    """Convert a LlamaParse v2 structured page to a ``Page`` object."""
    blocks = None
    if HierarchyLevel[level] >= HierarchyLevel.BLOCK:
        blocks = []
        for item in items_page.items:
            item_type = getattr(item, 'type', None)
            if item_type == 'table':
                blocks.append(_convert_table_block(item, items_page.page_number))
            elif item_type == 'image':
                blocks.append(_convert_image_block(item, items_page.page_number))
            else:
                blocks.append(_convert_text_block(item, items_page.page_number))

    source_data: dict = {}
    if meta_page:
        source_data['metadata'] = meta_page.model_dump()

    return Page(
        number=items_page.page_number,
        width=items_page.page_width,
        height=items_page.page_height,
        text=page_text,
        blocks=blocks,
        source_data=source_data,
    )

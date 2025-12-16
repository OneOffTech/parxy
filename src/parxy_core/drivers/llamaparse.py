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
from parxy_core.models import Document, Page, BoundingBox, TextBlock, HierarchyLevel
from parxy_core.exceptions import (
    ParsingException,
    AuthenticationException,
    FileNotFoundException,
)

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
                "Install with 'pip install parxy[llama]'"
            ) from e

        self.__client = LlamaParse(
            api_key=self._config.api_key.get_secret_value()
            if self._config and self._config.api_key
            else None,
            **self._config.model_dump() if self._config else {},
        )

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
        try:
            filename, stream = self.handle_file_input(file)
            extra_info = {'file_name': filename if len(filename) > 0 else 'default'}
            with self._trace_parse(filename, stream, **kwargs) as span:
                res = self.__client.parse(stream, extra_info=extra_info)
                span.set_attribute('output.document', res.model_dump_json())
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
        converted_document.parsing_metadata['job_error'] = res.error
        converted_document.parsing_metadata['job_error_code'] = res.error_code
        converted_document.parsing_metadata['job_status'] = res.status

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

import io
import json

import validators

from typing import TYPE_CHECKING

from parxy_core.models.config import LlmWhispererConfig

from parxy_core.tracing.utils import trace_with_output

# Type hints that will be available at runtime when llm whisperer is installed
if TYPE_CHECKING:
    from unstract.llmwhisperer import LLMWhispererClientV2
else:
    # Placeholder types for when package is not installed
    LLMWhispererClientV2 = None

from parxy_core.drivers import Driver
from parxy_core.exceptions import (
    FileNotFoundException,
    ParsingException,
    AuthenticationException,
)
from parxy_core.models import Document, Page


class LlmWhispererDriver(Driver):
    """Unstract LLMWhisperer API driver implementation.

    This parser interacts with the LLMWhisperer cloud service to extract page-level text from documents.

    Attributes
    ----------
    supported_levels : list of str
        The supported extraction level: `page`.
    client : LLMWhispererClientV2
        The LLMWhisperer client instance.
    """

    SERVICE_NAME = 'llmwhisperer'

    supported_levels: list[str] = ['page', 'block']

    _config: LlmWhispererConfig

    def _initialize_driver(self):
        """Initialize the LlmWhisperer driver."""

        try:
            from unstract.llmwhisperer import LLMWhispererClientV2
        except ImportError as e:
            raise ImportError(
                'LlmWhisperer dependencies not installed. '
                "Install with 'pip install parxy[llmwhisperer]'"
            ) from e

        self.__client = LLMWhispererClientV2(
            api_key=self._config.api_key.get_secret_value()
            if self._config and self._config.api_key
            else None,
            **self._config.model_dump() if self._config else {},
        )

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'page',
        **kwargs,
    ) -> Document:
        """Parse a document using LLMWhisperer.

        Parameters
        ----
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Must be one of `supported_levels`. Default is `"page"`.
        raw : bool, optional
            If True, return the raw response dict from LLMWhisperer instead of a `Document`. Default is False.
        **kwargs :
            Additional arguments passed to the LLMWhisperer client (e.g., `wait_timeout`).

        Returns
        -------
        Document or dict
            A parsed `Document` in unified format, or the raw response dict if `raw=True`.
        """

        from unstract.llmwhisperer.client_v2 import LLMWhispererClientException

        if level == 'block':
            level = 'page'  # Only page is really supported, added block as it is the default for Parxy

        self._validate_level(level)

        try:
            filename, stream = self.handle_file_input(file)
            with self._trace_parse(filename, stream, **kwargs) as span:
                res = self.__client.whisper(
                    file_path=filename,
                    stream=io.BytesIO(stream),
                    wait_for_completion=True,
                    wait_timeout=200,  # TODO: Handle configuration of args
                    # wait_timeout=kwargs.get("wait_timeout", 200),
                    # **kwargs,
                )
                span.set_attribute('output.document', json.dumps(res))
        except FileNotFoundError as fex:
            raise FileNotFoundException(fex, self.SERVICE_NAME) from fex
        except LLMWhispererClientException as wex:
            if wex.value['status_code'] in (401, 403):
                raise AuthenticationException(
                    message=str(wex.error_message()),
                    service=self.SERVICE_NAME,
                    details=wex.value,
                )  # from wex
            else:
                raise ParsingException(
                    wex.error_message if hasattr(wex, 'error_message') else str(wex),
                    self.SERVICE_NAME,
                    details=wex.value,
                ) from wex

        doc = llmwhisperer_to_parxy(res)
        doc.filename = filename
        return doc


@trace_with_output('converting')
def llmwhisperer_to_parxy(
    doc: dict,
) -> Document:
    """Convert a raw LLMWhisperer response dict to a `Document` object.

    Parameters
    ----
    doc : dict
        The response dict returned by the LLMWhisperer client.

    Returns
    -------
    Document
        The converted `Document` in unified format.
    """
    pages = []
    for page_number, page_text in enumerate(
        doc['extraction']['result_text'].split('<<<\x0c')[:-1]
    ):
        pages.append(
            Page(
                number=page_number,
                text=page_text,
                source_data=doc['extraction']['metadata'].get(str(page_number), None),
            )
        )
    document_source_data = doc['extraction']
    document_source_data.pop('result_text')
    document_source_data.pop('metadata')
    return Document(pages=pages, source_data=document_source_data)

import io

import validators

from typing import TYPE_CHECKING


# Type hints that will be available at runtime when llm whisperer is installed
if TYPE_CHECKING:
    from unstract.llmwhisperer import LLMWhispererClientV2
    from unstract.llmwhisperer.client_v2 import LLMWhispererClientException
else:
    # Placeholder types for when package is not installed
    LLMWhispererClientV2 = None
    LLMWhispererClientException = None

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

    def _initialize_driver(self):
        """Initialize the LlmWhisperer driver."""

        try:
            from unstract.llmwhisperer import LLMWhispererClientV2
        except ImportError as e:
            raise ImportError(
                'LlmWhisperer dependencies not installed. '
                "Install with 'pip install parxy-core[llmwhisperer]'"
            ) from e

        self.__client = LLMWhispererClientV2(**self._config)

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
        if level == 'block':
            level = 'page'  # Only page is really supported, added block as it is the default for Parxy

        self._validate_level(level)

        stream = None
        if isinstance(file, str):
            if validators.url(file) is True:
                stream = Driver.get_stream_from_url(filename=file)
                file = ''
        elif isinstance(file, io.BytesIO):
            stream = file
            file = ''
        elif isinstance(file, bytes):
            stream = io.BytesIO(file)
            file = ''
        else:
            raise ValueError(
                'The given file is not supported. Expected `str` or bytes-like.'
            )

        try:
            res = self.__client.whisper(
                file_path=file,
                stream=stream,
                wait_for_completion=True,
                wait_timeout=200,  # TODO: Handle configuration of args
                # wait_timeout=kwargs.get("wait_timeout", 200),
                # **kwargs,
            )
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
                    wex.error_message(), self.SERVICE_NAME, details=wex.value
                ) from wex

        doc = llmwhisperer_to_parxy(res)
        doc.filename = file
        return doc


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

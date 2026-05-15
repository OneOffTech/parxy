"""LiteParse HTTP driver for parxy."""

import io
from pathlib import Path
from urllib.parse import urljoin

import validators
import httpx

from parxy_core.drivers import Driver
from parxy_core.exceptions import ParsingException, RateLimitException
from parxy_core.models import Document, Page
from parxy_core.models.config import LiteParseConfig


class LiteParseDriver(Driver):
    """PDF/document parser using the self-hosted LiteParse HTTP service.

    Calls POST /parse on the LiteParse server and maps the ParsedPage
    response array to the Parxy Document model.
    """

    supported_levels = ['page', 'block']

    _config: LiteParseConfig

    def _initialize_driver(self):
        if httpx is None:
            raise ImportError(
                'httpx is required. Install with: pip install parxy[liteparse]'
            )

        if validators.url(self._config.base_url, simple_host=True) is not True:
            raise ValueError(
                f'Invalid base URL. Expected URL, found [{self._config.base_url}].'
            )

        return self

    def _handle(
        self, file: str | io.BytesIO | bytes, level: str = 'page', **kwargs
    ) -> Document:

        if level == 'block':
            level = 'page'

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            url = urljoin(self._config.base_url.rstrip('/') + '/', 'parse')
            fname = Path(filename).name if filename else 'document.pdf'

            try:
                with httpx.Client() as client:  # type: ignore[union-attr]
                    response = client.post(
                        url,
                        files={'file': (fname, stream, 'application/octet-stream')},
                    )
            except httpx.ConnectError as e:  # type: ignore[union-attr]
                raise ParsingException(
                    message=f'Could not connect to LiteParse service at {self._config.base_url}',
                    service='LiteParse',
                ) from e

            if response.status_code == 429:
                raise RateLimitException(
                    message='Rate limit exceeded',
                    service='LiteParse',
                )

            if response.status_code != 200:
                raise ParsingException(
                    message=f'LiteParse service returned HTTP {response.status_code}',
                    service='LiteParse',
                    details={'status_code': response.status_code},
                )

            data = response.json()
            pages = [
                Page(
                    number=p['pageNum'],
                    width=p.get('width'),
                    height=p.get('height'),
                    text=p.get('text', ''),
                    blocks=None,
                )
                for p in data.get('pages', [])
            ]

            span.set_attribute('output.pages', len(pages))

        return Document(
            filename=filename,
            pages=pages,
        )

"""LiteParse HTTP driver for parxy."""

import io
import json
from pathlib import Path
from urllib.parse import urljoin

import validators
import httpx

from parxy_core.drivers import Driver
from parxy_core.exceptions import ParsingException, RateLimitException
from parxy_core.models import Document, Page
from parxy_core.models.models import BoundingBox, Style, TextBlock
from parxy_core.models.config import LiteParseConfig


def _to_camel_case(name: str) -> str:
    parts = name.split('_')
    return parts[0] + ''.join(p.title() for p in parts[1:])


def _map_text_block(item: dict, page_number: int) -> TextBlock:
    x, y, w, h = item['x'], item['y'], item['width'], item['height']
    style = Style(
        font_name=item.get('fontName'),
        font_size=item.get('fontSize'),
    )
    return TextBlock(
        type='text',
        text=item.get('str', ''),
        page=page_number,
        bbox=BoundingBox(x0=x, y0=y, x1=x + w, y1=y + h),
        style=style if style.font_name or style.font_size else None,
    )


def _map_page(p: dict, level: str) -> Page:
    page_number = p['pageNum']
    blocks = (
        [_map_text_block(item, page_number) for item in p.get('textItems', [])]
        if level == 'block'
        else None
    )
    return Page(
        number=page_number,
        width=p.get('width'),
        height=p.get('height'),
        text=p.get('text', ''),
        blocks=blocks,
        source_data=p,
    )


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

    def _build_parse_config(
        self,
        target_pages: str | None = None,
        password: str | None = None,
        **overrides,
    ) -> str:
        """Serialize parse config fields to camelCase JSON for the LiteParse API."""
        data = self._config.model_dump(exclude={'base_url', 'timeout'})
        data.update({k: v for k, v in overrides.items() if k in data})
        result = {_to_camel_case(k): v for k, v in data.items() if v is not None}
        result['outputFormat'] = 'json'
        if target_pages is not None:
            result['targetPages'] = target_pages
        if password is not None:
            result['password'] = password
        return json.dumps(result)

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'page',
        target_pages: str | None = None,
        password: str | None = None,
        **kwargs,
    ) -> Document:

        filename, stream = self.handle_file_input(file)

        # Separate LiteParse config overrides from tracing/span kwargs
        config_fields = set(LiteParseConfig.model_fields) - {'base_url'}
        config_overrides = {}
        for key in list(kwargs.keys()):
            if key in config_fields:
                config_overrides[key] = kwargs.pop(key)

        with self._trace_parse(filename, stream, **kwargs) as span:
            url = urljoin(self._config.base_url.rstrip('/') + '/', 'parse')
            fname = Path(filename).name if filename else 'document.pdf'
            parse_config = self._build_parse_config(
                target_pages=target_pages, password=password, **config_overrides
            )

            try:
                with httpx.Client(timeout=self._config.timeout) as client:  # type: ignore[union-attr]
                    response = client.post(
                        url,
                        data={'config': parse_config},
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
            pages = [_map_page(p, level) for p in data.get('pages', [])]

            span.set_attribute('output.pages', len(pages))

        return Document(
            filename=filename,
            pages=pages,
        )

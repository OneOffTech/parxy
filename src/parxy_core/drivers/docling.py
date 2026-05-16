"""Docling Serve backend driver for parxy.

IBM Docling Serve provides high-quality PDF to JSON conversion via a REST API.
Requires a running docling-serve instance.

Documentation: https://github.com/docling-project/docling-serve

Configuration:
    Environment variables: PARXY_DOCLING_BASE_URL, PARXY_DOCLING_DO_OCR, etc.
    Config file: .env file with parxy_docling_ prefix

Example .env configuration:
    PARXY_DOCLING_BASE_URL=http://localhost:5001
    PARXY_DOCLING_API_KEY=secret
    PARXY_DOCLING_DO_OCR=false
    PARXY_DOCLING_PDF_BACKEND=dlparse_v2
    PARXY_DOCLING_TABLE_MODE=accurate
    PARXY_DOCLING_INCLUDE_IMAGES=false
"""

import base64
import io
from typing import Optional

import validators

from parxy_core.drivers import Driver
from parxy_core.exceptions import AuthenticationException, ParsingException
from parxy_core.models import (
    BoundingBox,
    Document,
    ImageBlock,
    Page,
    TableBlock,
    TextBlock,
)

_PER_CALL_OPTIONS = frozenset({
    'do_ocr',
    'pdf_backend',
    'table_mode',
    'include_images',
    'images_scale',
    'do_picture_classification',
    'do_picture_description',
})

DOCLING_LABEL_TO_ROLE: dict[str, str] = {
    'title': 'doc-title',
    'section_header': 'heading',
    'paragraph': 'paragraph',
    'list_item': 'list',
    'code': 'generic',
    'formula': 'generic',
    'caption': 'generic',
    'footnote': 'doc-footnote',
    'page_header': 'doc-pageheader',
    'page_footer': 'doc-pagefooter',
    'table': 'table',
    'picture': 'figure',
    'chart': 'figure',
    'document_index': 'generic',
    'checkbox_selected': 'generic',
    'checkbox_unselected': 'generic',
}


class DoclingDriver(Driver):
    """PDF parser using IBM Docling Serve API.

    Calls a running docling-serve instance for document processing.
    Docling uses deep learning models for document understanding.

    By default, OCR is DISABLED. Enable via:
        - Environment: PARXY_DOCLING_DO_OCR=true
        - Config: parxy_docling_do_ocr=true in .env

    Requires a running docling-serve instance. Quick start:
        docker run -p 5001:5001 ghcr.io/docling-project/docling-serve-cu128:v1.18.0

    Per-call options (passed as kwargs to parse()):
        do_ocr, pdf_backend, table_mode, include_images, images_scale,
        do_picture_classification, do_picture_description
    """

    supported_levels = ['page', 'block']

    def _initialize_driver(self):
        try:
            import httpx  # noqa: F401
        except ImportError as e:
            raise ImportError(
                'httpx is required. Install with: pip install parxy[docling]'
            ) from e

        if self._config:
            self._base_url = getattr(self._config, 'base_url', 'http://localhost:5001').rstrip('/')
            self._api_key = getattr(self._config, 'api_key', None)
            self._timeout = getattr(self._config, 'timeout', 120.0)
            self._poll_wait = getattr(self._config, 'poll_wait', 5.0)
        else:
            self._base_url = 'http://localhost:5001'
            self._api_key = None
            self._timeout = 120.0
            self._poll_wait = 5.0

        return self

    def _get_opt(self, overrides: dict, key: str, default=None):
        if key in overrides:
            return overrides[key]
        if self._config and hasattr(self._config, key):
            val = getattr(self._config, key)
            if val is not None:
                return val
        return default

    def _build_headers(self) -> dict:
        headers: dict = {}
        if self._api_key:
            api_key_value = (
                self._api_key.get_secret_value()
                if hasattr(self._api_key, 'get_secret_value')
                else self._api_key
            )
            headers['X-Api-Key'] = api_key_value
        return headers

    def _build_options(self, overrides: dict) -> dict:
        opts: dict = {
            'to_formats': ['json'],
            'do_ocr': self._get_opt(overrides, 'do_ocr', False),
            'do_table_structure': True,
            'pdf_backend': self._get_opt(overrides, 'pdf_backend', 'docling_parse'),
            'table_mode': self._get_opt(overrides, 'table_mode', 'accurate'),
            'include_images': self._get_opt(overrides, 'include_images', False),
            'abort_on_error': False,
        }

        images_scale = self._get_opt(overrides, 'images_scale', None)
        if images_scale is not None:
            opts['images_scale'] = float(images_scale)

        if self._get_opt(overrides, 'do_picture_classification', False):
            opts['do_picture_classification'] = True

        if self._get_opt(overrides, 'do_picture_description', False):
            opts['do_picture_description'] = True

        return opts

    def _handle(
        self, file: str | io.BytesIO | bytes, level: str = 'page', **kwargs
    ) -> Document:
        """Parse a document via the Docling Serve async API (blocking).

        Submits the job to the async endpoint, polls until complete, then
        fetches and returns the result. Transparently blocking from the
        caller's perspective.

        Parameters
        ----------
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Default is "page".
        **kwargs : dict
            Per-call configuration overrides. Supported options:

            - do_ocr: Enable OCR on bitmap content
            - pdf_backend: PDF backend (dlparse_v2, pypdfium2, etc.)
            - table_mode: Table extraction mode ('fast' or 'accurate')
            - include_images: Include images in output (default False)
            - images_scale: Scale factor for images
            - do_picture_classification: Classify pictures
            - do_picture_description: Generate picture descriptions

        Returns
        -------
        Document
            A parsed Document in unified format.
        """
        import httpx

        overrides = {k: v for k, v in kwargs.items() if k in _PER_CALL_OPTIONS}

        is_url = isinstance(file, str) and validators.url(file) is True

        if is_url:
            filename = file
            # Use URL bytes as stand-in for tracing hash/size; the actual
            # download is delegated to docling-serve
            stream_for_trace = file.encode('utf-8')
        else:
            filename, stream_for_trace = self.handle_file_input(file)

        with self._trace_parse(filename, stream_for_trace, **kwargs) as span:
            headers = self._build_headers()
            options = self._build_options(overrides)

            span.set_attribute('docling.do_ocr', options['do_ocr'])
            span.set_attribute('docling.pdf_backend', options['pdf_backend'])
            span.set_attribute('docling.table_mode', options['table_mode'])
            span.set_attribute('docling.include_images', options['include_images'])
            if 'images_scale' in options:
                span.set_attribute('docling.images_scale', options['images_scale'])
            if options.get('do_picture_classification'):
                span.set_attribute('docling.do_picture_classification', True)
            if options.get('do_picture_description'):
                span.set_attribute('docling.do_picture_description', True)

            if is_url:
                payload: dict = {
                    'options': options,
                    'sources': [{'kind': 'http', 'url': file}],
                }
            else:
                b64_data = base64.b64encode(stream_for_trace).decode('utf-8')
                upload_filename = (
                    filename.replace('\\', '/').rsplit('/', 1)[-1]
                    if filename
                    else 'document.pdf'
                )
                payload = {
                    'options': options,
                    'sources': [
                        {
                            'kind': 'file',
                            'base64_string': b64_data,
                            'filename': upload_filename,
                        }
                    ],
                }

            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(
                        f'{self._base_url}/v1/convert/source/async',
                        json=payload,
                        headers=headers,
                    )

                    if response.status_code == 401:
                        raise AuthenticationException(
                            'Authentication failed. Check PARXY_DOCLING_API_KEY.',
                            self.__class__,
                        )
                    if response.status_code != 200:
                        raise ParsingException(
                            f'Docling API error {response.status_code}: {response.text[:200]}',
                            self.__class__,
                        )

                    task_id = response.json().get('task_id')
                    if not task_id:
                        raise ParsingException(
                            'Docling async API did not return a task_id',
                            self.__class__,
                        )

                    data = self._poll_for_result(client, task_id, headers)

            except httpx.ConnectError as e:
                raise ParsingException(
                    f'Cannot connect to Docling server at {self._base_url}: {e}',
                    self.__class__,
                ) from e
            except httpx.TimeoutException as e:
                raise ParsingException(
                    f'Timeout connecting to Docling server at {self._base_url}',
                    self.__class__,
                ) from e

            if data.get('status') not in ('success', 'partial_success'):
                errors = data.get('errors', [])
                raise ParsingException(
                    f'Docling processing failed: {errors}', self.__class__
                )

            json_content = data.get('document', {}).get('json_content')

            if not json_content:
                raise ParsingException(
                    'Docling API returned empty JSON content', self.__class__
                )

            document = _docling_json_to_document(json_content, filename=filename, level=level)
            span.set_attribute('output.pages', len(document.pages))

        return document

    def _poll_for_result(self, client, task_id: str, headers: dict) -> dict:
        """Poll until the async task completes, then fetch and return the result."""
        import time
        import httpx

        deadline = time.monotonic() + self._timeout
        poll_read_timeout = self._poll_wait + 10.0

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ParsingException(
                    f'Docling processing timed out after {self._timeout}s (task {task_id})',
                    self.__class__,
                )

            wait = int(min(self._poll_wait, remaining))
            poll_resp = client.get(
                f'{self._base_url}/v1/status/poll/{task_id}',
                params={'wait': wait},
                headers=headers,
                timeout=httpx.Timeout(
                    connect=10.0, read=poll_read_timeout, write=10.0, pool=5.0
                ),
            )

            if poll_resp.status_code != 200:
                raise ParsingException(
                    f'Docling poll error {poll_resp.status_code}: {poll_resp.text[:200]}',
                    self.__class__,
                )

            status_data = poll_resp.json()
            task_status = status_data.get('task_status', '')
            task_meta = status_data.get('task_meta') or {}
            num_docs = task_meta.get('num_docs', 0)
            num_processed = task_meta.get('num_processed', 0)

            if task_status == 'failure':
                raise ParsingException(
                    f'Docling processing failed (task {task_id})',
                    self.__class__,
                )

            if task_status in ('success', 'partial_success'):
                break
            if num_docs > 0 and num_processed >= num_docs:
                break

        result_resp = client.get(
            f'{self._base_url}/v1/result/{task_id}',
            headers=headers,
        )
        if result_resp.status_code != 200:
            raise ParsingException(
                f'Docling result fetch error {result_resp.status_code}: {result_resp.text[:200]}',
                self.__class__,
            )
        return result_resp.json()


def _docling_json_to_document(json_content: dict, filename: str, level: str) -> Document:
    """Convert a Docling JSON document to a parxy Document."""
    items_by_ref: dict[str, tuple[str, dict]] = {}
    for i, item in enumerate(json_content.get('texts', [])):
        items_by_ref[item.get('self_ref', f'#/texts/{i}')] = ('text', item)
    for i, item in enumerate(json_content.get('tables', [])):
        items_by_ref[item.get('self_ref', f'#/tables/{i}')] = ('table', item)
    for i, item in enumerate(json_content.get('pictures', [])):
        items_by_ref[item.get('self_ref', f'#/pictures/{i}')] = ('picture', item)

    groups_by_ref: dict[str, dict] = {
        g.get('self_ref', f'#/groups/{i}'): g
        for i, g in enumerate(json_content.get('groups', []))
    }

    ordered: list[tuple[str, dict]] = []
    _traverse(json_content.get('body', {}), items_by_ref, groups_by_ref, ordered)

    # Fallback when body is missing or empty: sort by page then top-most bbox
    # (descending t = top-to-bottom in Docling BOTTOMLEFT coordinates)
    if not ordered:
        all_items: list = []
        for _, (item_type, item_data) in items_by_ref.items():
            prov = item_data.get('prov', [{}])
            p = prov[0] if prov else {}
            all_items.append((
                p.get('page_no', 1),
                -p.get('bbox', {}).get('t', 0.0),
                item_type,
                item_data,
            ))
        all_items.sort(key=lambda x: (x[0], x[1]))
        ordered = [(t, d) for _, _, t, d in all_items]

    items_by_page: dict[int, list[tuple[str, dict]]] = {}
    for item_type, item_data in ordered:
        prov = item_data.get('prov', [{}])
        page_no = (prov[0] if prov else {}).get('page_no', 1)
        items_by_page.setdefault(page_no, []).append((item_type, item_data))

    raw_pages: dict[str, dict] = json_content.get('pages', {})
    if raw_pages:
        page_nos = sorted(int(k) for k in raw_pages.keys())
    elif items_by_page:
        page_nos = sorted(items_by_page.keys())
    else:
        page_nos = []

    do_blocks = level == 'block'
    pages: list[Page] = []

    for page_no in page_nos:
        raw_page = raw_pages.get(str(page_no), {})
        size = raw_page.get('size', {})
        width: Optional[float] = size.get('width')
        height: Optional[float] = size.get('height')
        page_items = items_by_page.get(page_no, [])

        if do_blocks:
            blocks: list = []
            text_parts: list[str] = []
            for item_type, item_data in page_items:
                if item_type == 'text':
                    block = _make_text_block(item_data, page_no)
                    blocks.append(block)
                    if block.text:
                        text_parts.append(block.text)
                elif item_type == 'table':
                    block = _make_table_block(item_data, page_no)
                    blocks.append(block)
                    if block.text:
                        text_parts.append(block.text)
                elif item_type == 'picture':
                    blocks.append(_make_image_block(item_data, page_no))
            pages.append(Page(
                number=page_no,
                width=width,
                height=height,
                text='\n'.join(text_parts),
                blocks=blocks if blocks else None,
            ))
        else:
            text_parts = []
            for item_type, item_data in page_items:
                if item_type == 'text':
                    text = item_data.get('text', '') or ''
                    if text:
                        text_parts.append(text)
                elif item_type == 'table':
                    md = _table_to_markdown(item_data)
                    if md:
                        text_parts.append(md)
            pages.append(Page(
                number=page_no,
                width=width,
                height=height,
                text='\n'.join(text_parts),
                blocks=None,
            ))

    return Document(filename=filename, pages=pages)


def _traverse(
    node: dict,
    items_by_ref: dict[str, tuple[str, dict]],
    groups_by_ref: dict[str, dict],
    result: list[tuple[str, dict]],
) -> None:
    for child in node.get('children', []):
        ref = child.get('$ref', '')
        if ref in items_by_ref:
            result.append(items_by_ref[ref])
        elif ref in groups_by_ref:
            _traverse(groups_by_ref[ref], items_by_ref, groups_by_ref, result)


def _extract_bbox(prov_list: list) -> Optional[BoundingBox]:
    if not prov_list:
        return None
    bbox = prov_list[0].get('bbox', {})
    if not bbox:
        return None
    # Docling BOTTOMLEFT coords: l=left, r=right, t=top-y, b=bottom-y
    return BoundingBox(
        x0=bbox.get('l', 0.0),
        y0=bbox.get('b', 0.0),
        x1=bbox.get('r', 0.0),
        y1=bbox.get('t', 0.0),
    )


def _make_text_block(item: dict, page_no: int) -> TextBlock:
    label = item.get('label', 'paragraph')
    role = DOCLING_LABEL_TO_ROLE.get(label, 'paragraph')
    return TextBlock(
        type='text',
        role=role,
        category=label,
        level=item.get('level'),
        text=item.get('text', '') or '',
        bbox=_extract_bbox(item.get('prov', [])),
        page=page_no,
    )


def _make_table_block(item: dict, page_no: int) -> TableBlock:
    label = item.get('label', 'table')
    role = DOCLING_LABEL_TO_ROLE.get(label, 'table')
    return TableBlock(
        type='table',
        role=role,
        category=label,
        text=_table_to_markdown(item),
        bbox=_extract_bbox(item.get('prov', [])),
        page=page_no,
    )


def _make_image_block(item: dict, page_no: int) -> ImageBlock:
    label = item.get('label', 'picture')
    role = DOCLING_LABEL_TO_ROLE.get(label, 'figure')
    captions = item.get('captions', [])
    alt_text = captions[0].get('text', '') if captions else None
    return ImageBlock(
        type='image',
        role=role,
        category=label,
        alt_text=alt_text or None,
        bbox=_extract_bbox(item.get('prov', [])),
        page=page_no,
    )


def _table_to_markdown(table_item: dict) -> str:
    grid = table_item.get('data', {}).get('grid', [])
    if not grid:
        return ''

    rows = []
    for row in grid:
        cells = [cell.get('text', '') if cell else '' for cell in row]
        rows.append('| ' + ' | '.join(cells) + ' |')

    if rows:
        num_cols = len(grid[0]) if grid[0] else 0
        separator = '| ' + ' | '.join(['---'] * num_cols) + ' |'
        rows.insert(1, separator)

    return '\n'.join(rows)

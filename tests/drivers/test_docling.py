import os
import pytest
import httpx
from unittest.mock import Mock, patch, MagicMock

from parxy_core.models import Page, TextBlock, TableBlock, ImageBlock

from parxy_core.drivers import DoclingDriver
from parxy_core.exceptions import FileNotFoundException, AuthenticationException, ParsingException

_DOCLING_URL = 'http://localhost:5001'


def _is_docling_available() -> bool:
    try:
        with httpx.Client(timeout=2.0) as client:
            client.get(_DOCLING_URL)
        return True
    except Exception:
        return False


docling_live = pytest.mark.skipif(
    not _is_docling_available(),
    reason='Docling Serve not available at localhost:5001',
)


def _docling_response(pages: dict, texts=None, tables=None, pictures=None, groups=None):
    """Build a minimal successful Docling Serve API response."""
    texts = texts or []
    tables = tables or []
    pictures = pictures or []
    groups = groups or []

    body_children = (
        [{'$ref': t['self_ref']} for t in texts]
        + [{'$ref': t['self_ref']} for t in tables]
        + [{'$ref': p['self_ref']} for p in pictures]
    )

    return {
        'document': {
            'json_content': {
                'schema_name': 'DoclingDocument',
                'version': '1.0.0',
                'pages': pages,
                'texts': texts,
                'tables': tables,
                'pictures': pictures,
                'groups': groups,
                'body': {
                    'self_ref': '#/body',
                    'children': body_children,
                    'label': 'unspecified',
                    'name': 'body',
                },
            }
        },
        'status': 'success',
        'processing_time': 0.5,
        'errors': [],
    }


def _mock_response(data: dict, status_code: int = 200):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.text = str(data)
    return resp


def _mock_submit_response(task_id: str = 'test-task-123'):
    """Submit response from the async endpoint."""
    return _mock_response({
        'task_id': task_id,
        'task_type': 'conversion',
        'task_status': 'started',
        'task_meta': {'num_docs': 1, 'num_processed': 0, 'num_succeeded': 0, 'num_failed': 0},
    })


def _mock_poll_done_response(task_id: str = 'test-task-123'):
    """Poll response indicating the task has completed."""
    return _mock_response({
        'task_id': task_id,
        'task_type': 'conversion',
        'task_status': 'success',
        'task_meta': {'num_docs': 1, 'num_processed': 1, 'num_succeeded': 1, 'num_failed': 0},
    })


def _mock_client(post_response, get_responses=None):
    """Return a context-manager-compatible httpx.Client mock."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=False)
    ctx.post.return_value = post_response
    if get_responses is not None:
        ctx.get.side_effect = get_responses
    return ctx


def _mock_async_client(result_data: dict, task_id: str = 'test-task-123'):
    """Mock the full async flow: submit → poll (done) → result fetch."""
    return _mock_client(
        _mock_submit_response(task_id),
        get_responses=[_mock_poll_done_response(task_id), _mock_response(result_data)],
    )


class TestDoclingDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    # ── construction ──────────────────────────────────────────────────────────

    def test_docling_driver_can_be_created(self):
        driver = DoclingDriver()

        assert driver.supported_levels == ['page', 'block']

    # ── level validation ──────────────────────────────────────────────────────

    def test_docling_driver_unrecognized_level_handled(self):
        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    # ── file not found ────────────────────────────────────────────────────────

    def test_docling_driver_handle_not_existing_file(self):
        driver = DoclingDriver()
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path)

    # ── page-level extraction ─────────────────────────────────────────────────

    @patch('httpx.Client')
    def test_docling_driver_read_document_page_level(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
            texts=[
                {
                    'self_ref': '#/texts/0',
                    'text': 'Hello world',
                    'label': 'paragraph',
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 720.0, 'r': 540.0, 'b': 700.0, 'coord_origin': 'BOTTOMLEFT'}}],
                }
            ],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.metadata is None
        assert len(document.pages) == 1
        page = document.pages[0]
        assert isinstance(page, Page)
        assert page.number == 1
        assert page.blocks is None
        assert page.text == 'Hello world'
        assert page.width == 595.3
        assert page.height == 841.9

    @patch('httpx.Client')
    def test_docling_driver_read_empty_document_page_level(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
            texts=[],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert len(document.pages) == 1
        assert document.pages[0].number == 1
        assert document.pages[0].text == ''
        assert document.pages[0].blocks is None

    @patch('httpx.Client')
    def test_docling_driver_keeps_empty_pages(self, MockClient):
        response_data = _docling_response(
            pages={
                '1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1},
                '2': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 2},
                '3': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 3},
            },
            texts=[
                {
                    'self_ref': '#/texts/0',
                    'text': 'Page one content',
                    'label': 'paragraph',
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 720.0, 'r': 540.0, 'b': 700.0, 'coord_origin': 'BOTTOMLEFT'}}],
                },
                {
                    'self_ref': '#/texts/1',
                    'text': 'Page three content',
                    'label': 'paragraph',
                    'prov': [{'page_no': 3, 'bbox': {'l': 72.0, 't': 720.0, 'r': 540.0, 'b': 700.0, 'coord_origin': 'BOTTOMLEFT'}}],
                },
            ],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert len(document.pages) == 3
        assert document.pages[0].number == 1
        assert document.pages[0].text == 'Page one content'
        assert document.pages[1].number == 2
        assert document.pages[1].text == ''
        assert document.pages[2].number == 3
        assert document.pages[2].text == 'Page three content'

    # ── block-level extraction ────────────────────────────────────────────────

    @patch('httpx.Client')
    def test_docling_driver_read_document_block_level(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
            texts=[
                {
                    'self_ref': '#/texts/0',
                    'text': 'Document title',
                    'label': 'title',
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 800.0, 'r': 540.0, 'b': 780.0, 'coord_origin': 'BOTTOMLEFT'}}],
                },
                {
                    'self_ref': '#/texts/1',
                    'text': 'Section heading',
                    'label': 'section_header',
                    'level': 1,
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 760.0, 'r': 540.0, 'b': 740.0, 'coord_origin': 'BOTTOMLEFT'}}],
                },
                {
                    'self_ref': '#/texts/2',
                    'text': 'A paragraph of text.',
                    'label': 'paragraph',
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 720.0, 'r': 540.0, 'b': 700.0, 'coord_origin': 'BOTTOMLEFT'}}],
                },
            ],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='block')

        assert document is not None
        assert len(document.pages) == 1
        page = document.pages[0]
        assert page.number == 1
        assert page.blocks is not None
        assert len(page.blocks) == 3

        title_block = page.blocks[0]
        assert isinstance(title_block, TextBlock)
        assert title_block.role == 'doc-title'
        assert title_block.category == 'title'
        assert title_block.text == 'Document title'

        heading_block = page.blocks[1]
        assert isinstance(heading_block, TextBlock)
        assert heading_block.role == 'heading'
        assert heading_block.level == 1

        para_block = page.blocks[2]
        assert isinstance(para_block, TextBlock)
        assert para_block.role == 'paragraph'
        assert para_block.text == 'A paragraph of text.'

    @patch('httpx.Client')
    def test_docling_driver_table_block(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
            tables=[
                {
                    'self_ref': '#/tables/0',
                    'label': 'table',
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 500.0, 'r': 540.0, 'b': 400.0, 'coord_origin': 'BOTTOMLEFT'}}],
                    'data': {
                        'num_rows': 2,
                        'num_cols': 2,
                        'grid': [
                            [{'text': 'Col A'}, {'text': 'Col B'}],
                            [{'text': 'Val 1'}, {'text': 'Val 2'}],
                        ],
                    },
                }
            ],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='block')

        assert len(document.pages) == 1
        page = document.pages[0]
        assert page.blocks is not None
        assert len(page.blocks) == 1
        block = page.blocks[0]
        assert isinstance(block, TableBlock)
        assert block.role == 'table'
        assert '| Col A | Col B |' in block.text
        assert '| Val 1 | Val 2 |' in block.text
        assert '| --- | --- |' in block.text

    @patch('httpx.Client')
    def test_docling_driver_image_block(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
            pictures=[
                {
                    'self_ref': '#/pictures/0',
                    'label': 'picture',
                    'prov': [{'page_no': 1, 'bbox': {'l': 100.0, 't': 600.0, 'r': 400.0, 'b': 450.0, 'coord_origin': 'BOTTOMLEFT'}}],
                    'captions': [{'text': 'Figure 1: A diagram'}],
                }
            ],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='block')

        assert len(document.pages) == 1
        page = document.pages[0]
        assert page.blocks is not None
        assert len(page.blocks) == 1
        block = page.blocks[0]
        assert isinstance(block, ImageBlock)
        assert block.role == 'figure'
        assert block.alt_text == 'Figure 1: A diagram'

    # ── bounding box ──────────────────────────────────────────────────────────

    @patch('httpx.Client')
    def test_docling_driver_block_bbox(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
            texts=[
                {
                    'self_ref': '#/texts/0',
                    'text': 'text',
                    'label': 'paragraph',
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 720.0, 'r': 540.0, 'b': 700.0, 'coord_origin': 'BOTTOMLEFT'}}],
                }
            ],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='block')

        block = document.pages[0].blocks[0]
        assert block.bbox is not None
        assert block.bbox.x0 == 72.0
        assert block.bbox.x1 == 540.0

    # ── API request structure ─────────────────────────────────────────────────

    @patch('httpx.Client')
    def test_docling_driver_sends_json_format(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
        )
        mock_ctx = _mock_async_client(response_data)
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        driver.parse(path, level='page')

        call_kwargs = mock_ctx.post.call_args
        payload = call_kwargs[1]['json'] if 'json' in call_kwargs[1] else call_kwargs[0][1]
        assert payload['options']['to_formats'] == ['json']
        assert 'sources' in payload
        assert payload['sources'][0]['kind'] == 'file'

    @patch('httpx.Client')
    def test_docling_driver_url_uses_http_sources(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
        )
        mock_ctx = _mock_async_client(response_data)
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        driver.parse('http://example.com/doc.pdf', level='page')

        call_kwargs = mock_ctx.post.call_args
        payload = call_kwargs[1]['json'] if 'json' in call_kwargs[1] else call_kwargs[0][1]
        assert 'sources' in payload
        assert payload['sources'][0]['kind'] == 'http'
        assert payload['sources'][0]['url'] == 'http://example.com/doc.pdf'

    @patch('httpx.Client')
    def test_docling_driver_per_call_ocr_override(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
        )
        mock_ctx = _mock_async_client(response_data)
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        driver.parse(path, level='page', do_ocr=True)

        call_kwargs = mock_ctx.post.call_args
        payload = call_kwargs[1]['json'] if 'json' in call_kwargs[1] else call_kwargs[0][1]
        assert payload['options']['do_ocr'] is True

    @patch('httpx.Client')
    def test_docling_driver_per_call_pdf_backend_override(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
        )
        mock_ctx = _mock_async_client(response_data)
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        driver.parse(path, level='page', pdf_backend='pypdfium2', table_mode='fast')

        call_kwargs = mock_ctx.post.call_args
        payload = call_kwargs[1]['json'] if 'json' in call_kwargs[1] else call_kwargs[0][1]
        assert payload['options']['pdf_backend'] == 'pypdfium2'
        assert payload['options']['table_mode'] == 'fast'

    @patch('httpx.Client')
    def test_docling_driver_include_images_default_false(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
        )
        mock_ctx = _mock_async_client(response_data)
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        driver.parse(path, level='page')

        call_kwargs = mock_ctx.post.call_args
        payload = call_kwargs[1]['json'] if 'json' in call_kwargs[1] else call_kwargs[0][1]
        assert payload['options']['include_images'] is False

    # ── error handling ────────────────────────────────────────────────────────

    @patch('httpx.Client')
    def test_docling_driver_auth_error(self, MockClient):
        mock_ctx = _mock_client(_mock_response({}, status_code=401))
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(AuthenticationException):
            driver.parse(path)

    @patch('httpx.Client')
    def test_docling_driver_server_error(self, MockClient):
        mock_ctx = _mock_client(_mock_response({'detail': 'Internal error'}, status_code=500))
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ParsingException):
            driver.parse(path)

    @patch('httpx.Client')
    def test_docling_driver_failure_status(self, MockClient):
        result_data = {
            'document': {'json_content': None},
            'status': 'failure',
            'errors': ['Unsupported format'],
            'processing_time': 0.1,
        }
        mock_ctx = _mock_client(
            _mock_submit_response(),
            get_responses=[_mock_poll_done_response(), _mock_response(result_data)],
        )
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ParsingException):
            driver.parse(path)

    @patch('httpx.Client')
    def test_docling_driver_poll_task_not_found(self, MockClient):
        mock_ctx = _mock_client(
            _mock_submit_response(),
            get_responses=[_mock_response({'detail': 'Not found'}, status_code=404)],
        )
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ParsingException, match='task not found'):
            driver.parse(path)

    @patch('httpx.Client')
    def test_docling_driver_connect_error(self, MockClient):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = Mock(return_value=mock_ctx)
        mock_ctx.__exit__ = Mock(return_value=False)
        mock_ctx.post.side_effect = httpx.ConnectError('Connection refused')
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ParsingException):
            driver.parse(path)

    @patch('httpx.Client')
    def test_docling_driver_remote_protocol_error(self, MockClient):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = Mock(return_value=mock_ctx)
        mock_ctx.__exit__ = Mock(return_value=False)
        mock_ctx.post.side_effect = httpx.RemoteProtocolError(
            'Server disconnected without sending a response.'
        )
        MockClient.return_value = mock_ctx

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ParsingException, match='Network error'):
            driver.parse(path)

    # ── tracing ───────────────────────────────────────────────────────────────

    @patch('httpx.Client')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_docling_driver_tracing_span_created(self, mock_tracer, MockClient):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        driver.parse(path, level='page')

        mock_tracer.span.assert_called()

        span_calls = mock_tracer.span.call_args_list
        doc_processing_call = [
            c for c in span_calls if c[0][0] == 'document-processing'
        ][0]

        assert doc_processing_call[1]['driver'] == 'DoclingDriver'
        assert doc_processing_call[1]['level'] == 'page'

        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'DoclingDriver'

    @patch('httpx.Client')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_docling_driver_tracing_exception_recorded(self, mock_tracer, MockClient):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = DoclingDriver()
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='page')

        mock_tracer.error.assert_called_once()
        error_call = mock_tracer.error.call_args
        assert error_call[0][0] == 'Parsing failed'

        mock_tracer.count.assert_called_once()

    # ── elapsed time ──────────────────────────────────────────────────────────

    @patch('httpx.Client')
    def test_docling_driver_records_elapsed_time(self, MockClient):
        response_data = _docling_response(
            pages={'1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1}},
            texts=[
                {
                    'self_ref': '#/texts/0',
                    'text': 'content',
                    'label': 'paragraph',
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 720.0, 'r': 540.0, 'b': 700.0, 'coord_origin': 'BOTTOMLEFT'}}],
                }
            ],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document.parsing_metadata is not None
        assert 'driver_elapsed_time' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['driver_elapsed_time'], float)
        assert document.parsing_metadata['driver_elapsed_time'] > 0

    # ── multi-page ────────────────────────────────────────────────────────────

    @patch('httpx.Client')
    def test_docling_driver_multi_page_page_numbers_start_at_1(self, MockClient):
        response_data = _docling_response(
            pages={
                '1': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 1},
                '2': {'size': {'width': 595.3, 'height': 841.9}, 'page_no': 2},
            },
            texts=[
                {
                    'self_ref': '#/texts/0',
                    'text': 'First page',
                    'label': 'paragraph',
                    'prov': [{'page_no': 1, 'bbox': {'l': 72.0, 't': 720.0, 'r': 540.0, 'b': 700.0, 'coord_origin': 'BOTTOMLEFT'}}],
                },
                {
                    'self_ref': '#/texts/1',
                    'text': 'Second page',
                    'label': 'paragraph',
                    'prov': [{'page_no': 2, 'bbox': {'l': 72.0, 't': 720.0, 'r': 540.0, 'b': 700.0, 'coord_origin': 'BOTTOMLEFT'}}],
                },
            ],
        )
        MockClient.return_value = _mock_async_client(response_data)

        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert len(document.pages) == 2
        assert document.pages[0].number == 1
        assert document.pages[0].text == 'First page'
        assert document.pages[1].number == 2
        assert document.pages[1].text == 'Second page'


@docling_live
class TestDoclingDriverLive:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_live_empty_doc_page_level(self):
        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert len(document.pages) == 1
        page = document.pages[0]
        assert isinstance(page, Page)
        assert page.number == 1
        assert page.blocks is None
        assert page.text == '1'

    def test_live_empty_doc_block_level(self):
        driver = DoclingDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='block')

        assert document is not None
        assert len(document.pages) == 1
        page = document.pages[0]
        assert isinstance(page, Page)
        assert page.number == 1
        assert page.blocks is not None
        assert len(page.blocks) == 1
        assert isinstance(page.blocks[0], TextBlock)
        assert page.blocks[0].role == 'doc-pagefooter'
        assert page.blocks[0].text == '1'

    def test_live_test_doc_page_level(self):
        driver = DoclingDriver()
        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert len(document.pages) == 1
        page = document.pages[0]
        assert isinstance(page, Page)
        assert page.number == 1
        assert page.blocks is None
        assert page.text == (
            'This is the header\n'
            'This is a test PDF to be used as input in unit tests\n'
            'This is a heading 1\n'
            'This is a paragraph below heading 1\n'
            '1'
        )

    def test_live_test_doc_block_level(self):
        driver = DoclingDriver()
        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document is not None
        assert len(document.pages) == 1
        page = document.pages[0]
        assert page.blocks is not None
        assert len(page.blocks) == 5

        assert isinstance(page.blocks[0], TextBlock)
        assert page.blocks[0].role == 'doc-pageheader'
        assert page.blocks[0].text == 'This is the header'

        assert isinstance(page.blocks[1], TextBlock)
        assert page.blocks[1].role == 'heading'
        assert page.blocks[1].text == 'This is a test PDF to be used as input in unit tests'

        assert isinstance(page.blocks[2], TextBlock)
        assert page.blocks[2].role == 'heading'
        assert page.blocks[2].text == 'This is a heading 1'

        assert isinstance(page.blocks[3], TextBlock)
        assert page.blocks[3].role == 'paragraph'
        assert page.blocks[3].text == 'This is a paragraph below heading 1'

        assert isinstance(page.blocks[4], TextBlock)
        assert page.blocks[4].role == 'doc-pagefooter'
        assert page.blocks[4].text == '1'

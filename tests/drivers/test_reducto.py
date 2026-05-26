import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from parxy_core.exceptions import AuthenticationException, FileNotFoundException
from parxy_core.models import Page, TextBlock, TableBlock, ImageBlock

from parxy_core.drivers import ReductoDriver
from parxy_core.models import ReductoConfig


@pytest.mark.skipif(
    os.getenv('GITHUB_ACTIONS') == 'true' or not os.getenv('PARXY_REDUCTO_API_KEY'),
    reason='External service required. Set PARXY_REDUCTO_API_KEY to run these tests.',
)
class TestReductoDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_reducto_driver_can_be_created(self):
        driver = ReductoDriver(ReductoConfig())

        assert driver.supported_levels == ['page', 'block']

    def test_reducto_driver_handle_invalid_key(self):
        driver = ReductoDriver(ReductoConfig(api_key='invalid'))

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(AuthenticationException):
            driver.parse(path)

    def test_reducto_driver_handle_not_existing_file(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path)

    def test_reducto_driver_unrecognized_level_handled(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_reducto_driver_read_empty_document_block_level(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path)

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) >= 1
        assert isinstance(document.pages[0], Page)
        assert isinstance(document.pages[0].text, str)

    def test_reducto_driver_read_empty_document_page_level(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) >= 1
        assert isinstance(document.pages[0], Page)
        assert isinstance(document.pages[0].text, str)
        assert document.pages[0].blocks is None

    def test_reducto_driver_read_document(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].number == 1
        assert isinstance(document.pages[0].text, str)
        assert len(document.pages[0].text) > 0

    def test_reducto_driver_read_document_as_blocks(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document is not None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0].blocks, list)
        assert len(document.pages[0].blocks) > 0

    def test_reducto_driver_read_document_with_tables(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('pdf-headings-images-tables.pdf')
        document = driver.parse(path, level='block')

        assert document is not None
        assert len(document.pages) > 0
        all_blocks = [b for page in document.pages for b in (page.blocks or [])]
        assert any(isinstance(b, TableBlock) for b in all_blocks)

    def test_reducto_driver_page_numbers_are_populated(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        for page in document.pages:
            assert isinstance(page.number, int)
            assert page.number >= 1

    def test_reducto_driver_parsing_metadata_populated(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document.parsing_metadata is not None
        assert 'job_id' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['job_id'], str)
        assert 'upload_file_id' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['upload_file_id'], str)
        assert 'duration' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['duration'], float)
        assert 'num_pages' in document.parsing_metadata
        assert document.parsing_metadata['num_pages'] >= 1

    def test_reducto_driver_cost_estimation_populated(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document.parsing_metadata is not None
        assert 'cost_estimation' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['cost_estimation'], (int, float))
        assert document.parsing_metadata['cost_estimation'] >= 0
        assert 'cost_estimation_unit' in document.parsing_metadata
        assert document.parsing_metadata['cost_estimation_unit'] == 'credits'

    def test_reducto_driver_records_elapsed_time(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document.parsing_metadata is not None
        assert 'driver_elapsed_time' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['driver_elapsed_time'], float)
        assert document.parsing_metadata['driver_elapsed_time'] > 0

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_reducto_driver_tracing_span_created(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        driver = ReductoDriver(ReductoConfig())
        path = self.__fixture_path('empty-doc.pdf')
        driver.parse(path, level='block')

        mock_tracer.span.assert_called()

        span_calls = mock_tracer.span.call_args_list
        doc_processing_call = [
            c for c in span_calls if c[0][0] == 'document-processing'
        ][0]

        assert doc_processing_call[1]['driver'] == 'ReductoDriver'
        assert doc_processing_call[1]['level'] == 'block'

        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'ReductoDriver'

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_reducto_driver_tracing_exception_recorded(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = ReductoDriver(ReductoConfig())
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='block')

        mock_tracer.error.assert_called_once()
        error_call = mock_tracer.error.call_args
        assert error_call[0][0] == 'Parsing failed'

        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.failures'
        assert count_call[1]['driver'] == 'ReductoDriver'


class TestReductoDriverUnit:
    """Unit tests that mock the Reducto client — no API key or network required."""

    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def _build_full_response(self, blocks=None, job_id='test-job-id', credits=3.0):
        """Build a realistic FullParseResponse using real SDK Pydantic models."""
        from reducto.lib.helpers import FullParseResponse
        from reducto.types.parse_usage import ParseUsage
        from reducto.types.shared.parse_response import (
            ResultFullResult,
            ResultFullResultChunk,
            ResultFullResultChunkBlock,
        )
        from reducto.types.bounding_box import BoundingBox as ReductoBox

        if blocks is None:
            bbox = ReductoBox(left=0.1, top=0.1, width=0.8, height=0.05, page=1)
            blocks = [
                ResultFullResultChunkBlock(
                    type='Text',
                    content='This is a test paragraph.',
                    bbox=bbox,
                )
            ]

        chunk = ResultFullResultChunk(
            blocks=blocks,
            content=' '.join(b.content for b in blocks),
            embed=' '.join(b.content for b in blocks),
        )
        result = ResultFullResult(chunks=[chunk], type='full')
        return FullParseResponse(
            duration=1.5,
            job_id=job_id,
            result=result,
            usage=ParseUsage(num_pages=1, credits=credits),
        )

    def _make_mock_client(self, full_response):
        """Return a mock Reducto client wired up with the given full_response."""
        mock_client = MagicMock()
        mock_upload = MagicMock()
        mock_upload.file_id = 'uploaded-file-id-abc'
        mock_client.upload.return_value = mock_upload
        mock_client.parse.run.return_value = MagicMock()
        return mock_client

    def test_reducto_driver_can_be_created(self):
        driver = ReductoDriver(ReductoConfig())

        assert driver.supported_levels == ['page', 'block']

    def test_reducto_driver_unrecognized_level_handled(self):
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_handle_not_existing_file(self, mock_create_client):
        mock_create_client.return_value = MagicMock()
        driver = ReductoDriver(ReductoConfig())

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path)

    @patch('reducto.lib.helpers.handle_url_response')
    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_parsing_metadata_populated(
        self, mock_create_client, mock_handle_url_response
    ):
        full_response = self._build_full_response(job_id='my-job-99', credits=6.0)
        mock_create_client.return_value = self._make_mock_client(full_response)
        mock_handle_url_response.return_value = full_response

        driver = ReductoDriver(ReductoConfig())
        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document.parsing_metadata is not None
        assert document.parsing_metadata['job_id'] == 'my-job-99'
        assert document.parsing_metadata['upload_file_id'] == 'uploaded-file-id-abc'
        assert document.parsing_metadata['duration'] == 1.5
        assert document.parsing_metadata['num_pages'] == 1
        assert document.parsing_metadata['cost_estimation'] == 6.0
        assert document.parsing_metadata['cost_estimation_unit'] == 'credits'

    @patch('reducto.lib.helpers.handle_url_response')
    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_upload_file_id_stored_in_metadata(
        self, mock_create_client, mock_handle_url_response
    ):
        full_response = self._build_full_response()
        mock_client = self._make_mock_client(full_response)
        mock_client.upload.return_value.file_id = 'specific-file-id-xyz'
        mock_create_client.return_value = mock_client
        mock_handle_url_response.return_value = full_response

        driver = ReductoDriver(ReductoConfig())
        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document.parsing_metadata['upload_file_id'] == 'specific-file-id-xyz'

    @patch('reducto.lib.helpers.handle_url_response')
    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_text_blocks_converted(
        self, mock_create_client, mock_handle_url_response
    ):
        from reducto.types.shared.parse_response import (
            ResultFullResultChunkBlock,
        )
        from reducto.types.bounding_box import BoundingBox as ReductoBox

        bbox = ReductoBox(left=0.0, top=0.0, width=1.0, height=0.1, page=1)
        blocks = [
            ResultFullResultChunkBlock(type='Text', content='A paragraph.', bbox=bbox),
            ResultFullResultChunkBlock(
                type='Section Header', content='A heading.', bbox=bbox
            ),
        ]
        full_response = self._build_full_response(blocks=blocks)
        mock_create_client.return_value = self._make_mock_client(full_response)
        mock_handle_url_response.return_value = full_response

        driver = ReductoDriver(ReductoConfig())
        document = driver.parse(self.__fixture_path('test-doc.pdf'), level='block')

        assert len(document.pages) == 1
        page_blocks = document.pages[0].blocks
        assert len(page_blocks) == 2
        assert all(isinstance(b, TextBlock) for b in page_blocks)
        assert page_blocks[0].role == 'paragraph'
        assert page_blocks[0].category == 'Text'
        assert page_blocks[1].role == 'heading'
        assert page_blocks[1].category == 'Section Header'

    @patch('reducto.lib.helpers.handle_url_response')
    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_table_blocks_converted(
        self, mock_create_client, mock_handle_url_response
    ):
        from reducto.types.shared.parse_response import (
            ResultFullResultChunkBlock,
        )
        from reducto.types.bounding_box import BoundingBox as ReductoBox

        bbox = ReductoBox(left=0.0, top=0.1, width=1.0, height=0.3, page=1)
        blocks = [
            ResultFullResultChunkBlock(
                type='Table', content='| col1 | col2 |\n| a | b |', bbox=bbox
            ),
        ]
        full_response = self._build_full_response(blocks=blocks)
        mock_create_client.return_value = self._make_mock_client(full_response)
        mock_handle_url_response.return_value = full_response

        driver = ReductoDriver(ReductoConfig())
        document = driver.parse(self.__fixture_path('test-doc.pdf'), level='block')

        page_blocks = document.pages[0].blocks
        assert len(page_blocks) == 1
        assert isinstance(page_blocks[0], TableBlock)
        assert page_blocks[0].role == 'table'
        assert page_blocks[0].text == '| col1 | col2 |\n| a | b |'

    @patch('reducto.lib.helpers.handle_url_response')
    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_image_blocks_converted(
        self, mock_create_client, mock_handle_url_response
    ):
        from reducto.types.shared.parse_response import (
            ResultFullResultChunkBlock,
        )
        from reducto.types.bounding_box import BoundingBox as ReductoBox

        bbox = ReductoBox(left=0.2, top=0.2, width=0.6, height=0.4, page=1)
        blocks = [
            ResultFullResultChunkBlock(
                type='Figure', content='A chart showing revenue.', bbox=bbox
            ),
        ]
        full_response = self._build_full_response(blocks=blocks)
        mock_create_client.return_value = self._make_mock_client(full_response)
        mock_handle_url_response.return_value = full_response

        driver = ReductoDriver(ReductoConfig())
        document = driver.parse(self.__fixture_path('test-doc.pdf'), level='block')

        page_blocks = document.pages[0].blocks
        assert len(page_blocks) == 1
        assert isinstance(page_blocks[0], ImageBlock)
        assert page_blocks[0].role == 'figure'
        assert page_blocks[0].alt_text == 'A chart showing revenue.'

    @patch('reducto.lib.helpers.handle_url_response')
    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_bounding_box_converted(
        self, mock_create_client, mock_handle_url_response
    ):
        from reducto.types.shared.parse_response import (
            ResultFullResultChunkBlock,
        )
        from reducto.types.bounding_box import BoundingBox as ReductoBox

        bbox = ReductoBox(left=0.1, top=0.2, width=0.5, height=0.3, page=1)
        blocks = [
            ResultFullResultChunkBlock(
                type='Text', content='Block with bbox.', bbox=bbox
            )
        ]
        full_response = self._build_full_response(blocks=blocks)
        mock_create_client.return_value = self._make_mock_client(full_response)
        mock_handle_url_response.return_value = full_response

        driver = ReductoDriver(ReductoConfig())
        document = driver.parse(self.__fixture_path('test-doc.pdf'), level='block')

        block = document.pages[0].blocks[0]
        assert block.bbox is not None
        assert block.bbox.x0 == pytest.approx(0.1)
        assert block.bbox.y0 == pytest.approx(0.2)
        assert block.bbox.x1 == pytest.approx(0.6)
        assert block.bbox.y1 == pytest.approx(0.5)

    @patch('reducto.lib.helpers.handle_url_response')
    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_page_level_has_no_blocks(
        self, mock_create_client, mock_handle_url_response
    ):
        full_response = self._build_full_response()
        mock_create_client.return_value = self._make_mock_client(full_response)
        mock_handle_url_response.return_value = full_response

        driver = ReductoDriver(ReductoConfig())
        document = driver.parse(self.__fixture_path('test-doc.pdf'), level='page')

        assert len(document.pages) == 1
        assert document.pages[0].blocks is None
        assert isinstance(document.pages[0].text, str)

    @patch('reducto.lib.helpers.handle_url_response')
    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    def test_reducto_driver_blocks_grouped_by_page(
        self, mock_create_client, mock_handle_url_response
    ):
        from reducto.types.shared.parse_response import (
            ResultFullResult,
            ResultFullResultChunk,
            ResultFullResultChunkBlock,
        )
        from reducto.types.bounding_box import BoundingBox as ReductoBox
        from reducto.lib.helpers import FullParseResponse
        from reducto.types.parse_usage import ParseUsage

        bbox_p1 = ReductoBox(left=0.0, top=0.0, width=1.0, height=0.1, page=1)
        bbox_p2 = ReductoBox(left=0.0, top=0.0, width=1.0, height=0.1, page=2)
        blocks = [
            ResultFullResultChunkBlock(
                type='Text', content='Page 1 text.', bbox=bbox_p1
            ),
            ResultFullResultChunkBlock(
                type='Text', content='Page 2 text.', bbox=bbox_p2
            ),
        ]
        chunk = ResultFullResultChunk(
            blocks=blocks, content='Page 1 text. Page 2 text.', embed=''
        )
        result = ResultFullResult(chunks=[chunk], type='full')
        full_response = FullParseResponse(
            duration=2.0,
            job_id='multi-page-job',
            result=result,
            usage=ParseUsage(num_pages=2, credits=6.0),
        )

        mock_create_client.return_value = self._make_mock_client(full_response)
        mock_handle_url_response.return_value = full_response

        driver = ReductoDriver(ReductoConfig())
        document = driver.parse(self.__fixture_path('test-doc.pdf'), level='block')

        assert len(document.pages) == 2
        assert document.pages[0].number == 1
        assert len(document.pages[0].blocks) == 1
        assert document.pages[0].blocks[0].text == 'Page 1 text.'
        assert document.pages[1].number == 2
        assert len(document.pages[1].blocks) == 1
        assert document.pages[1].blocks[0].text == 'Page 2 text.'

    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_reducto_driver_handles_authentication_error(
        self, mock_tracer, mock_create_client
    ):
        from reducto._exceptions import AuthenticationError as ReductoAuthError
        from httpx import Response, Request

        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.upload.side_effect = ReductoAuthError(
            'Invalid API key',
            response=Response(
                status_code=401,
                request=Request('POST', 'https://platform.reducto.ai/upload'),
            ),
            body={'error': 'Invalid API key'},
        )

        driver = ReductoDriver(ReductoConfig(api_key='invalid'))
        path = self.__fixture_path('test-doc.pdf')

        with pytest.raises(AuthenticationException) as excinfo:
            driver.parse(path)

        assert excinfo.value.service == 'ReductoDriver'

    @patch('parxy_core.drivers.reducto.ReductoDriver._create_client')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_reducto_driver_tracing_exception_recorded(
        self, mock_tracer, mock_create_client
    ):
        mock_create_client.return_value = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = ReductoDriver(ReductoConfig())
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='block')

        mock_tracer.error.assert_called_once()
        assert mock_tracer.error.call_args[0][0] == 'Parsing failed'

        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.failures'
        assert count_call[1]['driver'] == 'ReductoDriver'

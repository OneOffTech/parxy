import os
import pytest
import httpx
from unittest.mock import Mock, patch, MagicMock

from parxy_core.models import Page
from parxy_core.models.config import LiteParseConfig
from parxy_core.drivers import LiteParseDriver
from parxy_core.exceptions import (
    FileNotFoundException,
    ParsingException,
    RateLimitException,
)


def _liteparse_service_available(base_url: str = 'http://localhost:5000') -> bool:
    try:
        with httpx.Client(timeout=2.0) as client:
            client.get(base_url)
        return True
    except Exception:
        return False


def _make_mock_client(status_code: int, json_body: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_body

    mock_client = MagicMock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.post.return_value = mock_response
    return mock_client


class TestLiteParseDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_liteparse_driver_can_be_created(self):
        driver = LiteParseDriver(config=LiteParseConfig())

        assert driver.supported_levels == ['page', 'block']

    def test_liteparse_driver_unrecognized_level_handled(self):
        driver = LiteParseDriver(config=LiteParseConfig())
        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_liteparse_driver_handle_not_existing_file(self):
        driver = LiteParseDriver(config=LiteParseConfig())
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path)

    def test_liteparse_driver_read_empty_document_page_level(self):
        mock_client = _make_mock_client(
            status_code=200,
            json_body={
                'pages': [
                    {
                        'pageNum': 1,
                        'width': 612.0,
                        'height': 792.0,
                        'text': '1',
                        'textItems': [],
                    },
                ]
            },
        )

        with patch(
            'parxy_core.drivers.liteparse.httpx.Client', return_value=mock_client
        ):
            driver = LiteParseDriver(config=LiteParseConfig())
            path = self.__fixture_path('empty-doc.pdf')
            document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].number == 1
        assert document.pages[0].width == 612.0
        assert document.pages[0].height == 792.0
        assert document.pages[0].blocks is None
        assert document.pages[0].text == '1'

    def test_liteparse_driver_read_document(self):
        expected_text = (
            'This is the header\n'
            'This is a test PDF to be used as input in unit\n'
            'tests\n'
            'This is a heading 1\n'
            'This is a paragraph below heading 1'
        )
        mock_client = _make_mock_client(
            status_code=200,
            json_body={
                'pages': [
                    {
                        'pageNum': 1,
                        'width': 612.0,
                        'height': 792.0,
                        'text': expected_text,
                        'textItems': [],
                    },
                ]
            },
        )

        with patch(
            'parxy_core.drivers.liteparse.httpx.Client', return_value=mock_client
        ):
            driver = LiteParseDriver(config=LiteParseConfig())
            path = self.__fixture_path('test-doc.pdf')
            document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].number == 1
        assert document.pages[0].blocks is None
        assert document.pages[0].text == expected_text

    def test_liteparse_driver_rate_limit_raises_exception(self):
        mock_client = _make_mock_client(status_code=429, json_body={})

        with patch(
            'parxy_core.drivers.liteparse.httpx.Client', return_value=mock_client
        ):
            driver = LiteParseDriver(config=LiteParseConfig())
            path = self.__fixture_path('test-doc.pdf')

            with pytest.raises(RateLimitException):
                driver.parse(path)

    def test_liteparse_driver_http_error_raises_parsing_exception(self):
        mock_client = _make_mock_client(status_code=500, json_body={})

        with patch(
            'parxy_core.drivers.liteparse.httpx.Client', return_value=mock_client
        ):
            driver = LiteParseDriver(config=LiteParseConfig())
            path = self.__fixture_path('test-doc.pdf')

            with pytest.raises(ParsingException):
                driver.parse(path)

    def test_liteparse_driver_connection_error_raises_parsing_exception(self):
        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError('Connection refused')

        with patch(
            'parxy_core.drivers.liteparse.httpx.Client', return_value=mock_client
        ):
            driver = LiteParseDriver(config=LiteParseConfig())
            path = self.__fixture_path('test-doc.pdf')

            with pytest.raises(ParsingException):
                driver.parse(path)

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_liteparse_driver_tracing_span_created(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        mock_client = _make_mock_client(
            status_code=200,
            json_body={
                'pages': [
                    {
                        'pageNum': 1,
                        'width': 612.0,
                        'height': 792.0,
                        'text': '1',
                        'textItems': [],
                    }
                ]
            },
        )

        with patch(
            'parxy_core.drivers.liteparse.httpx.Client', return_value=mock_client
        ):
            driver = LiteParseDriver(config=LiteParseConfig())
            path = self.__fixture_path('empty-doc.pdf')
            driver.parse(path, level='page')

        mock_tracer.span.assert_called()
        span_calls = mock_tracer.span.call_args_list
        doc_processing_call = [
            c for c in span_calls if c[0][0] == 'document-processing'
        ][0]
        assert doc_processing_call[1]['driver'] == 'LiteParseDriver'
        assert doc_processing_call[1]['level'] == 'page'

        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'LiteParseDriver'

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_liteparse_driver_tracing_exception_recorded(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = LiteParseDriver(config=LiteParseConfig())
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='page')

        mock_tracer.error.assert_called_once()
        assert mock_tracer.error.call_args[0][0] == 'Parsing failed'
        mock_tracer.count.assert_called_once()

    def test_liteparse_driver_records_elapsed_time(self):
        mock_client = _make_mock_client(
            status_code=200,
            json_body={
                'pages': [
                    {
                        'pageNum': 1,
                        'width': 612.0,
                        'height': 792.0,
                        'text': '1',
                        'textItems': [],
                    }
                ]
            },
        )

        with patch(
            'parxy_core.drivers.liteparse.httpx.Client', return_value=mock_client
        ):
            driver = LiteParseDriver(config=LiteParseConfig())
            path = self.__fixture_path('empty-doc.pdf')
            document = driver.parse(path, level='page')

        assert document.parsing_metadata is not None
        assert 'driver_elapsed_time' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['driver_elapsed_time'], float)
        assert document.parsing_metadata['driver_elapsed_time'] > 0

    def test_liteparse_driver_custom_base_url(self):
        driver = LiteParseDriver(
            config=LiteParseConfig(base_url='http://my-server:8080')
        )

        assert driver._config.base_url == 'http://my-server:8080'

    def test_liteparse_driver_posts_to_correct_url(self):
        mock_client = _make_mock_client(
            status_code=200,
            json_body={
                'pages': [
                    {
                        'pageNum': 1,
                        'width': 612.0,
                        'height': 792.0,
                        'text': '1',
                        'textItems': [],
                    }
                ]
            },
        )

        with patch(
            'parxy_core.drivers.liteparse.httpx.Client', return_value=mock_client
        ):
            driver = LiteParseDriver(
                config=LiteParseConfig(base_url='http://my-server:8080')
            )
            path = self.__fixture_path('empty-doc.pdf')
            driver.parse(path, level='page')

        call_url = mock_client.post.call_args[0][0]
        assert call_url == 'http://my-server:8080/parse'


@pytest.mark.skipif(
    not _liteparse_service_available(),
    reason='LiteParse service not available at http://localhost:5000',
)
class TestLiteParseDriverIntegration:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_liteparse_driver_read_document_page_level(self):
        expected_text = (
            'This is the header\n\n'
            'This is a test PDF to be used as input in unit\n'
            'tests\n\n'
            'This is a heading 1\n'
            'This is a paragraph below heading 1\n\n\n\n\n\n\n\n\n\n\n1'
        )
        driver = LiteParseDriver(config=LiteParseConfig())
        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].number == 1
        assert document.pages[0].width == 612
        assert document.pages[0].height == 792
        assert document.pages[0].blocks is None
        assert document.pages[0].text == expected_text

    def test_liteparse_driver_read_document_block_level(self):
        driver = LiteParseDriver(config=LiteParseConfig())
        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document is not None
        assert len(document.pages) == 1
        assert document.pages[0].number == 1

    def test_liteparse_driver_returns_parsing_metadata(self):
        driver = LiteParseDriver(config=LiteParseConfig())
        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document.parsing_metadata is not None
        assert 'driver_elapsed_time' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['driver_elapsed_time'], float)
        assert document.parsing_metadata['driver_elapsed_time'] > 0

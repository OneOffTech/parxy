import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from parxy_core.exceptions import (
    AuthenticationException,
    FileNotFoundException,
)
from parxy_core.models import TextBlock, Page

from parxy_core.drivers import LlamaParseDriver
from parxy_core.models import LlamaParseConfig


@pytest.mark.skipif(
    os.getenv('GITHUB_ACTIONS') == 'true',
    reason='External service required, skipping tests in GitHub Actions.',
)
class TestLlamaParseDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_llamaparse_driver_can_be_created(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        assert driver.supported_levels == ['page', 'block']

    def test_llamaparse_driver_handle_invalid_key(self):
        driver = LlamaParseDriver(LlamaParseConfig(api_key='invalid'))

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(AuthenticationException) as excinfo:
            driver.parse(path)

    def test_llamaparse_driver_handle_not_existing_file(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException) as excinfo:
            driver.parse(path)

    def test_llamaparse_driver_unrecognized_level_handled(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_llamaparse_driver_read_empty_document_block_level(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path)

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].text == '1'
        assert len(document.pages[0].blocks) == 1
        assert isinstance(document.pages[0].blocks[0], TextBlock)

    def test_llamaparse_driver_read_empty_document_page_level(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].text == '1'

    def test_llamaparse_driver_read_document(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert (
            document.pages[0].text
            == 'This is the header\n\nThis is a test PDF to be used as input in unit\ntests\n\nThis is a heading 1\nThis is a paragraph below heading 1\n\n1'
        )

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_llamaparse_driver_tracing_span_created(self, mock_tracer):
        # Setup mocks for the span context manager
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        driver = LlamaParseDriver(LlamaParseConfig())
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='block')

        # Verify tracer.span was called to create span
        mock_tracer.span.assert_called()

        # Find the 'document-processing' span call (from abstract_driver.parse)
        span_calls = mock_tracer.span.call_args_list
        doc_processing_call = [
            c for c in span_calls if c[0][0] == 'document-processing'
        ][0]

        # Verify span attributes
        assert doc_processing_call[1]['driver'] == 'LlamaParseDriver'
        assert doc_processing_call[1]['level'] == 'block'

        # Verify counter was incremented via tracer.count
        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'LlamaParseDriver'

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_llamaparse_driver_tracing_exception_recorded(self, mock_tracer):
        # Setup mocks
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = LlamaParseDriver(LlamaParseConfig())
        path = self.__fixture_path('non-existing-file.pdf')

        # Attempt to parse non-existing file
        with pytest.raises(FileNotFoundException):
            driver.parse(path)

        # Verify error was logged via tracer.error
        mock_tracer.error.assert_called_once()
        error_call = mock_tracer.error.call_args
        assert error_call[0][0] == 'Parsing failed'

        # Verify documents.failures counter was incremented
        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.failures'
        assert count_call[1]['driver'] == 'LlamaParseDriver'

    def test_llamaparse_driver_extracts_parsing_modes(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        # Verify parsing_metadata exists and contains parsing modes
        assert document.parsing_metadata is not None

        # Check if page_parsing_modes is in parsing_metadata (it may not be if LlamaParse doesn't provide it)
        # This is conditional because the actual LlamaParse response may or may not include parsingMode
        if 'page_parsing_modes' in document.parsing_metadata:
            parsing_modes = document.parsing_metadata['page_parsing_modes']
            assert isinstance(parsing_modes, dict)
            # Verify it's a mapping of page numbers to parsing modes
            for page_num, mode in parsing_modes.items():
                assert isinstance(page_num, int)
                assert isinstance(mode, str)

            # Verify parsing_mode_counts exists
            assert 'parsing_mode_counts' in document.parsing_metadata
            parsing_mode_counts = document.parsing_metadata['parsing_mode_counts']
            assert isinstance(parsing_mode_counts, dict)

            # Verify counts are correct
            for mode, count in parsing_mode_counts.items():
                assert isinstance(mode, str)
                assert isinstance(count, int)
                assert count > 0

            # Verify total count matches number of pages with parsing modes
            assert sum(parsing_mode_counts.values()) == len(parsing_modes)

            # Verify cost_estimation exists
            assert 'cost_estimation' in document.parsing_metadata
            cost_estimation = document.parsing_metadata['cost_estimation']
            assert isinstance(cost_estimation, int)
            assert cost_estimation > 0

            # Verify cost estimation is reasonable (at least 1 credit per page minimum)
            assert cost_estimation >= len(parsing_modes)

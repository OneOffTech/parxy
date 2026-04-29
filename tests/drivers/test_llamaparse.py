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

        with pytest.raises(AuthenticationException):
            driver.parse(path)

    def test_llamaparse_driver_handle_not_existing_file(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
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
        assert len(document.pages) >= 1
        assert isinstance(document.pages[0], Page)
        assert isinstance(document.pages[0].text, str)

    def test_llamaparse_driver_read_empty_document_page_level(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) >= 1
        assert isinstance(document.pages[0], Page)
        assert isinstance(document.pages[0].text, str)

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
        assert document.pages[0].number == 1
        assert isinstance(document.pages[0].text, str)
        assert len(document.pages[0].text) > 0

    def test_llamaparse_driver_read_document_as_blocks(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document is not None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0].blocks, list)
        assert len(document.pages[0].blocks) > 0

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

    def test_llamaparse_driver_parsing_metadata_populated(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='block')

        assert document.parsing_metadata is not None
        assert 'job_id' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['job_id'], str)
        assert 'job_status' in document.parsing_metadata
        assert document.parsing_metadata['job_status'] == 'COMPLETED'
        assert 'tier' in document.parsing_metadata
        assert 'cost_estimation' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['cost_estimation'], (int, float))
        assert document.parsing_metadata['cost_estimation'] >= 0
        assert 'cost_estimation_unit' in document.parsing_metadata
        assert document.parsing_metadata['cost_estimation_unit'] == 'credits'

    def test_llamaparse_driver_legacy_parse_mode_maps_to_tier(self):
        driver = LlamaParseDriver(LlamaParseConfig(parse_mode='parse_page_with_llm'))

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.parsing_metadata is not None
        assert document.parsing_metadata.get('tier') == 'cost_effective'

    def test_llamaparse_driver_tier_override_per_call(self):
        driver = LlamaParseDriver(LlamaParseConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page', tier='fast')

        assert document is not None
        assert document.parsing_metadata is not None
        assert document.parsing_metadata.get('tier') == 'fast'

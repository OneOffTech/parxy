import os
import pytest
import re
from unittest.mock import Mock, patch, MagicMock

from parxy_core.exceptions import (
    AuthenticationException,
    FileNotFoundException,
)
from parxy_core.models import TextBlock, Page

from parxy_core.drivers import LandingAIADEDriver
from parxy_core.models import LandingAIConfig


@pytest.mark.skipif(
    os.getenv('GITHUB_ACTIONS') == 'true',
    reason='External service required, skipping tests in GitHub Actions.',
)
class TestLandingAIADEDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_landingai_driver_can_be_created(self):
        driver = LandingAIADEDriver(LandingAIConfig())

        assert driver.supported_levels == ['page', 'block']

    def test_landingai_driver_handle_invalid_key(self):
        driver = LandingAIADEDriver(LandingAIConfig(api_key='invalid'))

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(AuthenticationException) as excinfo:
            driver.parse(path)

    def test_landingai_driver_handle_not_existing_file(self):
        driver = LandingAIADEDriver(LandingAIConfig())

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException) as excinfo:
            driver.parse(path)

    def test_landingai_driver_unrecognized_level_handled(self):
        driver = LandingAIADEDriver(LandingAIConfig())

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_landingai_driver_read_empty_document_block_level(self):
        driver = LandingAIADEDriver(LandingAIConfig())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path)

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        # The output contain a generated anchor tag like <a id='1e6096c7-6acf-4933-bdbc-a16f4264b4c2'></a>
        # we strip them before verifying the page content
        stripped_text = (
            re.sub(r'<[^>]+>', '', document.pages[0].text).replace('\n', '').strip()
        )
        assert stripped_text == '1'
        assert len(document.pages[0].blocks) == 1
        assert isinstance(document.pages[0].blocks[0], TextBlock)

    def test_landingai_driver_read_empty_document_page_level(self):
        driver = LandingAIADEDriver(LandingAIConfig())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        stripped_text = (
            re.sub(r'<[^>]+>', '', document.pages[0].text).replace('\n', '').strip()
        )
        assert stripped_text == '1'

    def test_landingai_driver_read_document(self):
        driver = LandingAIADEDriver(LandingAIConfig())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)

        # The output contain a generated anchor tag like <a id='1e6096c7-6acf-4933-bdbc-a16f4264b4c2'></a>
        # we strip them before verifying the page content
        stripped_text = re.sub(r'<[^>]+>', '', document.pages[0].text).strip()
        assert (
            stripped_text
            == 'This is the header\n\n\nThis is a test PDF to be used as input in unit tests\n\n\n# This is a heading 1\nThis is a paragraph below heading 1\n\n\n1'
        )

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_landingai_driver_tracing_span_created(self, mock_tracer):
        # Setup mocks for the span context manager
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        driver = LandingAIADEDriver(LandingAIConfig())
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
        assert doc_processing_call[1]['driver'] == 'LandingAIADEDriver'
        assert doc_processing_call[1]['level'] == 'block'

        # Verify counter was incremented via tracer.count
        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'LandingAIADEDriver'

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_landingai_driver_tracing_exception_recorded(self, mock_tracer):
        # Setup mocks
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = LandingAIADEDriver(LandingAIConfig())
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
        assert count_call[1]['driver'] == 'LandingAIADEDriver'

    @patch('landingai_ade.LandingAIADE')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_landingai_driver_cost_estimation(self, mock_tracer, mock_client_class):
        """Test that cost estimation is extracted from parse response metadata"""
        # Setup tracing mocks
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        # Setup client mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock parse response with metadata including credit usage
        # Based on https://docs.landing.ai/ade/ade-json-response.md
        mock_metadata = MagicMock()
        mock_metadata.credit_usage = 6.0
        mock_metadata.duration_ms = 24382
        mock_metadata.filename = 'test-document.pdf'
        mock_metadata.job_id = 'td8wu72tq2g9l9tfgkwn3q3kp'
        mock_metadata.page_count = 2
        mock_metadata.version = 'dpt-2-20251103'
        mock_metadata.model_dump = Mock(
            return_value={
                'credit_usage': 6.0,
                'duration_ms': 24382,
                'filename': 'test-document.pdf',
                'job_id': 'td8wu72tq2g9l9tfgkwn3q3kp',
                'page_count': 2,
                'version': 'dpt-2-20251103',
            }
        )

        mock_chunk_1 = MagicMock()
        mock_chunk_1.markdown = 'Page 1 content'
        mock_chunk_1.type = 'text'
        mock_chunk_1.grounding = MagicMock()
        mock_chunk_1.grounding.page = 0
        mock_chunk_1.grounding.box = MagicMock()
        mock_chunk_1.grounding.box.left = 0.1
        mock_chunk_1.grounding.box.top = 0.1
        mock_chunk_1.grounding.box.right = 0.9
        mock_chunk_1.grounding.box.bottom = 0.5
        mock_chunk_1.model_dump = Mock(return_value={})

        mock_chunk_2 = MagicMock()
        mock_chunk_2.markdown = 'Page 2 content'
        mock_chunk_2.type = 'text'
        mock_chunk_2.grounding = MagicMock()
        mock_chunk_2.grounding.page = 1
        mock_chunk_2.grounding.box = MagicMock()
        mock_chunk_2.grounding.box.left = 0.1
        mock_chunk_2.grounding.box.top = 0.1
        mock_chunk_2.grounding.box.right = 0.9
        mock_chunk_2.grounding.box.bottom = 0.5
        mock_chunk_2.model_dump = Mock(return_value={})

        mock_response_metadata = MagicMock()
        mock_response_metadata.filename = 'test-document.pdf'
        mock_response_metadata.model_dump = Mock(return_value={})

        mock_response = MagicMock()
        mock_response.chunks = [mock_chunk_1, mock_chunk_2]
        mock_response.metadata = mock_metadata
        mock_response.model_dump_json = Mock(return_value='{}')

        mock_client.parse.return_value = mock_response

        # Create driver
        driver = LandingAIADEDriver(LandingAIConfig())

        # Parse document
        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path)

        # Verify cost estimation metadata
        assert document.parsing_metadata is not None
        assert 'cost_estimation' in document.parsing_metadata
        assert document.parsing_metadata['cost_estimation'] == 6.0
        assert document.parsing_metadata['cost_estimation_unit'] == 'credits'

        # Verify ADE details
        assert 'ade_details' in document.parsing_metadata
        ade_details = document.parsing_metadata['ade_details']
        assert ade_details['duration_ms'] == 24382
        assert ade_details['filename'] == 'test-document.pdf'
        assert ade_details['job_id'] == 'td8wu72tq2g9l9tfgkwn3q3kp'
        assert ade_details['page_count'] == 2
        assert ade_details['version'] == 'dpt-2-20251103'

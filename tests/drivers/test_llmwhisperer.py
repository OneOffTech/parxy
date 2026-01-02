import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from parxy_core.exceptions import (
    AuthenticationException,
    FileNotFoundException,
)
from parxy_core.models import Page

from parxy_core.drivers import LlmWhispererDriver
from parxy_core.models import LlmWhispererConfig


@pytest.mark.skipif(
    os.getenv('GITHUB_ACTIONS') == 'true',
    reason='External service required, skipping tests in GitHub Actions.',
)
class TestLlmWhispererDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_llmwhisperer_driver_can_be_created(self):
        driver = LlmWhispererDriver(LlmWhispererConfig())

        assert driver.supported_levels == ['page', 'block']

    def test_llmwhisperer_driver_handle_invalid_key(self):
        driver = LlmWhispererDriver(LlmWhispererConfig(api_key='invalid'))

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(AuthenticationException) as excinfo:
            driver.parse(path)

    def test_llmwhisperer_driver_handle_not_existing_file(self):
        driver = LlmWhispererDriver(LlmWhispererConfig())

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException) as excinfo:
            driver.parse(path)

    def test_llmwhisperer_driver_unrecognized_level_handled(self):
        driver = LlmWhispererDriver(LlmWhispererConfig())

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_llmwhisperer_driver_read_empty_document_page_level(self):
        driver = LlmWhispererDriver(LlmWhispererConfig())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].text == '\n\n1 \n'

    def test_llmwhisperer_driver_read_document(self):
        driver = LlmWhispererDriver(LlmWhispererConfig())

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
            == '\n\nThis is the header \n\nThis is a test PDF to be used as input in unit \n\ntests \n\nThis is a heading 1 \nThis is a paragraph below heading 1 \n\n                                                       1 \n'
        )

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_llmwhisperer_driver_tracing_span_created(self, mock_tracer):
        # Setup mocks for the span context manager
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        driver = LlmWhispererDriver(LlmWhispererConfig())
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        # Verify tracer.span was called to create span
        mock_tracer.span.assert_called()

        # Find the 'document-processing' span call (from abstract_driver.parse)
        span_calls = mock_tracer.span.call_args_list
        doc_processing_call = [
            c for c in span_calls if c[0][0] == 'document-processing'
        ][0]

        # Verify span attributes
        assert doc_processing_call[1]['driver'] == 'LlmWhispererDriver'
        assert doc_processing_call[1]['level'] == 'page'

        # Verify counter was incremented via tracer.count
        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'LlmWhispererDriver'

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_llmwhisperer_driver_tracing_exception_recorded(self, mock_tracer):
        # Setup mocks
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = LlmWhispererDriver(LlmWhispererConfig())
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
        assert count_call[1]['driver'] == 'LlmWhispererDriver'

    @patch('unstract.llmwhisperer.LLMWhispererClientV2')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_llmwhisperer_driver_mode_from_kwargs(self, mock_tracer, mock_client_class):
        """Test that mode parameter from kwargs is passed to whisper method"""
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
        
        # Mock whisper response
        mock_response = {
            'extraction': {
                'result_text': 'Test content\n<<<\x0c',
                'metadata': {'0': {'page_number': 0}}
            }
        }
        mock_client.whisper.return_value = mock_response
        mock_client.get_usage_info.return_value = None

        # Create driver with default mode in config
        config = LlmWhispererConfig(mode='form')
        driver = LlmWhispererDriver(config)
        
        # Use bytes input instead of file path to avoid file I/O
        test_data = b'%PDF-1.4 test content'
        
        # Parse with mode override in kwargs
        document = driver.parse(test_data, level='page', mode='high_quality')

        # Verify whisper was called with the mode from kwargs
        mock_client.whisper.assert_called_once()
        call_kwargs = mock_client.whisper.call_args[1]
        assert call_kwargs['mode'] == 'high_quality'

    @patch('unstract.llmwhisperer.LLMWhispererClientV2')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_llmwhisperer_driver_mode_from_config(self, mock_tracer, mock_client_class):
        """Test that mode parameter from config is used when not in kwargs"""
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
        
        # Mock whisper response
        mock_response = {
            'extraction': {
                'result_text': 'Test content\n<<<\x0c',
                'metadata': {'0': {'page_number': 0}}
            }
        }
        mock_client.whisper.return_value = mock_response
        mock_client.get_usage_info.return_value = None

        # Create driver with specific mode in config
        config = LlmWhispererConfig(mode='low_cost')
        driver = LlmWhispererDriver(config)
        
        # Use bytes input instead of file path to avoid file I/O
        test_data = b'%PDF-1.4 test content'
        
        # Parse without mode in kwargs
        document = driver.parse(test_data, level='page')

        # Verify whisper was called with the mode from config
        mock_client.whisper.assert_called_once()
        call_kwargs = mock_client.whisper.call_args[1]
        assert call_kwargs['mode'] == 'low_cost'

    @patch('unstract.llmwhisperer.LLMWhispererClientV2')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_llmwhisperer_driver_mode_cost_estimation(self, mock_tracer, mock_client_class):
        """Test that cost estimation uses the correct parsing mode"""
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
        
        # Mock whisper response with 2 pages including detail fields
        mock_response = {
            'extraction': {
                'result_text': 'Page 1\n<<<\x0cPage 2\n<<<\x0c',
                'metadata': {
                    '0': {'page_number': 0},
                    '1': {'page_number': 1}
                }
            },
            'whisper_hash': 'abc123def456',
            'mode': 'native_text',
            'completed_at': 'Mon, 10 Feb 2025 10:40:58 GMT',
            'processing_started_at': 'Mon, 10 Feb 2025 10:40:53 GMT',
            'processing_time_in_seconds': 5.0,
            'total_pages': 2,
            'requested_pages': 2,
            'processed_pages': 2,
            'upload_file_size_in_kb': 618.488,
            'tag': 'test_tag'
        }
        mock_client.whisper.return_value = mock_response
        
        # Mock usage info
        mock_usage_info = {
            'quota': 1000,
            'used': 50,
            'remaining': 950
        }
        mock_client.get_usage_info.return_value = mock_usage_info

        # Create driver with native_text mode (1/1000 credits per page)
        config = LlmWhispererConfig(mode='native_text')
        driver = LlmWhispererDriver(config)
        
        # Use bytes input instead of file path to avoid file I/O
        test_data = b'%PDF-1.4 test content'
        
        # Parse document
        document = driver.parse(test_data, level='page')

        # Verify cost estimation metadata
        assert document.parsing_metadata is not None
        assert 'parsing_mode' in document.parsing_metadata
        assert document.parsing_metadata['parsing_mode'] == 'native_text'
        assert 'cost_estimation' in document.parsing_metadata
        # 2 pages * (1/1000) credits per page = 0.002 credits
        assert document.parsing_metadata['cost_estimation'] == 0.002
        assert document.parsing_metadata['cost_estimation_unit'] == 'credits'
        assert document.parsing_metadata['pages_processed'] == 2
        
        # Verify whisper-specific metadata
        assert 'whisper_hash' in document.parsing_metadata
        assert document.parsing_metadata['whisper_hash'] == 'abc123def456'
        
        # Verify whisper details
        assert 'whisper_details' in document.parsing_metadata
        whisper_details = document.parsing_metadata['whisper_details']
        assert whisper_details['completed_at'] == 'Mon, 10 Feb 2025 10:40:58 GMT'
        assert whisper_details['processing_started_at'] == 'Mon, 10 Feb 2025 10:40:53 GMT'
        assert whisper_details['processing_time_in_seconds'] == 5.0
        assert whisper_details['total_pages'] == 2
        assert whisper_details['requested_pages'] == 2
        assert whisper_details['processed_pages'] == 2
        assert whisper_details['upload_file_size_in_kb'] == 618.488
        assert whisper_details['tag'] == 'test_tag'

    @patch('unstract.llmwhisperer.LLMWhispererClientV2')
    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_llmwhisperer_driver_metadata_extraction(self, mock_tracer, mock_client_class):
        """Test that whisper metadata is properly extracted from response"""
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
        
        # Mock whisper response with partial metadata (some fields missing)
        mock_response = {
            'extraction': {
                'result_text': 'Test content\n<<<\x0c',
                'metadata': {'0': {'page_number': 0}}
            },
            'whisper_hash': 'xyz789',
            'mode': 'high_quality',
            'processing_time_in_seconds': 3.5,
            'total_pages': 1
            # Other fields intentionally missing to test robustness
        }
        mock_client.whisper.return_value = mock_response
        mock_client.get_usage_info.return_value = None

        # Create driver
        config = LlmWhispererConfig(mode='form')
        driver = LlmWhispererDriver(config)
        
        # Use bytes input
        test_data = b'%PDF-1.4 test content'
        
        # Parse document
        document = driver.parse(test_data, level='page')

        # Verify whisper hash is extracted
        assert 'whisper_hash' in document.parsing_metadata
        assert document.parsing_metadata['whisper_hash'] == 'xyz789'
        
        # Verify mode from response takes precedence over config
        assert document.parsing_metadata['parsing_mode'] == 'high_quality'
        
        # Verify whisper details only contains fields that were present
        assert 'whisper_details' in document.parsing_metadata
        whisper_details = document.parsing_metadata['whisper_details']
        assert whisper_details['processing_time_in_seconds'] == 3.5
        assert whisper_details['total_pages'] == 1
        
        # These fields should not be present since they weren't in the response
        assert 'completed_at' not in whisper_details
        assert 'processing_started_at' not in whisper_details
        assert 'requested_pages' not in whisper_details
        assert 'tag' not in whisper_details

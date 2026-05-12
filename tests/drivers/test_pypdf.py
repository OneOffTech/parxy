import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from parxy_core.models import Page

from parxy_core.drivers import PyPDFDriver
from parxy_core.exceptions import FileNotFoundException


class TestPyPDFDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_pypdf_driver_can_be_created(self):
        driver = PyPDFDriver()

        assert driver.supported_levels == ['page']

    def test_pypdf_driver_unrecognized_level_handled(self):
        driver = PyPDFDriver()

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_pypdf_driver_handle_not_existing_file(self):
        driver = PyPDFDriver()

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='page')

    def test_pypdf_driver_read_empty_document_page_level(self):
        driver = PyPDFDriver()

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is not None
        assert document.metadata.title == 'Test document'
        assert document.metadata.author == 'Data House Author'
        assert document.metadata.subject is None
        assert document.metadata.keywords is None
        assert 'Microsoft' in document.metadata.creator
        assert 'Microsoft' in document.metadata.producer
        assert document.metadata.created_at == '2023-11-13T18:43:06'
        assert document.metadata.updated_at == document.metadata.created_at
        assert document.outline is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].blocks is None
        assert isinstance(document.pages[0].text, str)

    def test_pypdf_driver_read_document(self):
        driver = PyPDFDriver()

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.metadata is not None
        assert document.metadata.title == 'Test document'
        assert document.metadata.author == 'Data House Author'
        assert document.metadata.created_at == '2023-05-09T11:34:41'
        assert document.metadata.updated_at == document.metadata.created_at
        assert document.outline is not None
        assert len(document.outline) == 1
        assert document.outline[0] == 'This is a heading 1 -> 1'
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].blocks is None
        assert document.pages[0].text
        assert 'test' in document.pages[0].text.lower()

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_pypdf_driver_tracing_span_created(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        driver = PyPDFDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        mock_tracer.span.assert_called()

        span_calls = mock_tracer.span.call_args_list
        doc_processing_call = [
            c for c in span_calls if c[0][0] == 'document-processing'
        ][0]

        assert doc_processing_call[1]['driver'] == 'PyPDFDriver'
        assert doc_processing_call[1]['level'] == 'page'

        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'PyPDFDriver'

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_pypdf_driver_tracing_exception_recorded(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = PyPDFDriver()
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='page')

        mock_tracer.error.assert_called_once()
        error_call = mock_tracer.error.call_args
        assert error_call[0][0] == 'Parsing failed'

        mock_tracer.count.assert_called_once()

    def test_pypdf_driver_records_elapsed_time(self):
        driver = PyPDFDriver()

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document.parsing_metadata is not None
        assert 'driver_elapsed_time' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['driver_elapsed_time'], float)
        assert document.parsing_metadata['driver_elapsed_time'] > 0

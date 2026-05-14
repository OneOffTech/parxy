import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from parxy_core.models import Page

from parxy_core.drivers import PDFPlumberDriver
from parxy_core.exceptions import FileNotFoundException


class TestPDFPlumberDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_pdfplumber_driver_can_be_created(self):
        driver = PDFPlumberDriver()

        assert driver.supported_levels == ['page', 'block']

    def test_pdfplumber_driver_unrecognized_level_handled(self):
        driver = PDFPlumberDriver()

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_pdfplumber_driver_handle_not_existing_file(self):
        driver = PDFPlumberDriver()

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='page')

    def test_pdfplumber_driver_read_empty_document_page_level(self):
        driver = PDFPlumberDriver()

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].blocks is None
        assert document.pages[0].text == '1'
        assert document.pages[0].number == 1

    def test_pdfplumber_driver_read_document(self):
        driver = PDFPlumberDriver()

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].blocks is None
        assert document.pages[0].number == 1
        assert (
            document.pages[0].text
            == 'This is the header\nThis is a test PDF to be used as input in unit\ntests\nThis is a heading 1\nThis is a paragraph below heading 1\n1'
        )

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_pdfplumber_driver_tracing_span_created(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        driver = PDFPlumberDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        mock_tracer.span.assert_called()

        span_calls = mock_tracer.span.call_args_list
        doc_processing_call = [
            c for c in span_calls if c[0][0] == 'document-processing'
        ][0]

        assert doc_processing_call[1]['driver'] == 'PDFPlumberDriver'
        assert doc_processing_call[1]['level'] == 'page'

        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'PDFPlumberDriver'

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_pdfplumber_driver_tracing_exception_recorded(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = PDFPlumberDriver()
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='page')

        mock_tracer.error.assert_called_once()
        error_call = mock_tracer.error.call_args
        assert error_call[0][0] == 'Parsing failed'

        mock_tracer.count.assert_called_once()

    def test_pdfplumber_driver_records_elapsed_time(self):
        driver = PDFPlumberDriver()

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document.parsing_metadata is not None
        assert 'driver_elapsed_time' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['driver_elapsed_time'], float)
        assert document.parsing_metadata['driver_elapsed_time'] > 0

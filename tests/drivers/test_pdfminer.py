import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from parxy_core.models import Page, TocEntry

from parxy_core.drivers import PDFMinerDriver
from parxy_core.exceptions import FileNotFoundException


class TestPDFMinerDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_pdfminer_driver_can_be_created(self):
        driver = PDFMinerDriver()

        assert driver.supported_levels == ['page', 'block']

    def test_pdfminer_driver_unrecognized_level_handled(self):
        driver = PDFMinerDriver()

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_pdfminer_driver_handle_not_existing_file(self):
        driver = PDFMinerDriver()

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='page')

    def test_pdfminer_driver_read_empty_document_page_level(self):
        driver = PDFMinerDriver()

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].blocks is None
        assert document.pages[0].number == 1
        assert document.pages[0].text == '1'

    def test_pdfminer_driver_read_document(self):
        driver = PDFMinerDriver()

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
            == 'This is the header \nThis is a test PDF to be used as input in unit \ntests \nThis is a heading 1 \nThis is a paragraph below heading 1 \n1'
        )

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_pdfminer_driver_tracing_span_created(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.info = Mock()

        driver = PDFMinerDriver()
        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        mock_tracer.span.assert_called()

        span_calls = mock_tracer.span.call_args_list
        doc_processing_call = [
            c for c in span_calls if c[0][0] == 'document-processing'
        ][0]

        assert doc_processing_call[1]['driver'] == 'PDFMinerDriver'
        assert doc_processing_call[1]['level'] == 'page'

        mock_tracer.count.assert_called_once()
        count_call = mock_tracer.count.call_args
        assert count_call[0][0] == 'documents.processed'
        assert count_call[1]['driver'] == 'PDFMinerDriver'

    @patch('parxy_core.drivers.abstract_driver.tracer')
    def test_pdfminer_driver_tracing_exception_recorded(self, mock_tracer):
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer.span = Mock(return_value=mock_span)
        mock_tracer.count = Mock()
        mock_tracer.error = Mock()

        driver = PDFMinerDriver()
        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException):
            driver.parse(path, level='page')

        mock_tracer.error.assert_called_once()
        error_call = mock_tracer.error.call_args
        assert error_call[0][0] == 'Parsing failed'

        mock_tracer.count.assert_called_once()

    def test_pdfminer_driver_reads_outline(self):
        driver = PDFMinerDriver()

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document.outline is not None
        assert len(document.outline) == 1
        entry = document.outline[0]
        assert isinstance(entry, TocEntry)
        assert entry.title == 'This is a heading 1'
        assert entry.page == 1
        assert entry.level == 1
        assert entry.bbox is None

    def test_pdfminer_driver_empty_document_has_no_outline(self):
        driver = PDFMinerDriver()

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document.outline is None

    def test_pdfminer_driver_records_elapsed_time(self):
        driver = PDFMinerDriver()

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document.parsing_metadata is not None
        assert 'driver_elapsed_time' in document.parsing_metadata
        assert isinstance(document.parsing_metadata['driver_elapsed_time'], float)
        assert document.parsing_metadata['driver_elapsed_time'] > 0

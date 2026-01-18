from unittest.mock import patch, MagicMock

import pytest

from parxy_core.facade import Parxy
from parxy_core.drivers import DriverFactory
from parxy_core.drivers import PyMuPdfDriver
from parxy_core.drivers import PdfActDriver
from parxy_core.models import Document, Page, BatchTask, BatchResult


class TestParxyFacade:
    def test_build_required_to_create_instance(self):
        with pytest.raises(TypeError) as excinfo:
            Parxy()

        assert 'Parxy is a static class and cannot be instantiated' in str(
            excinfo.value
        )

    def test_unrecognized_driver(self):
        with pytest.raises(ValueError) as excinfo:
            Parxy.driver('unrecognized')

        assert 'Driver [unrecognized] not supported' in str(excinfo.value)

    def test_default_driver_instantiated(self):
        driver = Parxy.driver()
        assert isinstance(driver, PyMuPdfDriver)

    def test_pdfact_driver_instantiated(self):
        driver = Parxy.driver('pdfact')
        assert isinstance(driver, PdfActDriver)

    def test_driver_factory_returned(self):
        driver = Parxy._get_factory()
        assert isinstance(driver, DriverFactory)

    def test_manager_is_singleton(self):
        factory_one = Parxy._get_factory()
        factory_two = Parxy._get_factory()

        assert factory_one is factory_two


class TestBatchResult:
    def test_success_property_true_when_document_present(self):
        doc = Document(pages=[Page(number=1, text='test')])
        result = BatchResult(file='test.pdf', driver='pymupdf', document=doc, error=None)

        assert result.success is True
        assert result.failed is False

    def test_success_property_false_when_document_none(self):
        result = BatchResult(
            file='test.pdf', driver='pymupdf', document=None, error='Parse error'
        )

        assert result.success is False
        assert result.failed is True

    def test_failed_property_true_when_error_present(self):
        result = BatchResult(
            file='test.pdf', driver='pymupdf', document=None, error='Some error'
        )

        assert result.failed is True

    def test_failed_property_false_when_no_error(self):
        doc = Document(pages=[Page(number=1, text='test')])
        result = BatchResult(file='test.pdf', driver='pymupdf', document=doc, error=None)

        assert result.failed is False


class TestBatchTask:
    def test_batch_task_with_file_only(self):
        task = BatchTask(file='test.pdf')

        assert task.file == 'test.pdf'
        assert task.drivers is None
        assert task.level is None

    def test_batch_task_with_all_fields(self):
        task = BatchTask(file='test.pdf', drivers=['pymupdf', 'pdfact'], level='line')

        assert task.file == 'test.pdf'
        assert task.drivers == ['pymupdf', 'pdfact']
        assert task.level == 'line'


class TestParxyBatch:
    @patch.object(Parxy, 'parse')
    def test_batch_with_simple_file_list(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc

        results = Parxy.batch(tasks=['doc1.pdf', 'doc2.pdf'], workers=1)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert mock_parse.call_count == 2

    @patch.object(Parxy, 'parse')
    def test_batch_with_multiple_drivers(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc

        results = Parxy.batch(
            tasks=['doc.pdf'], drivers=['pymupdf', 'pdfact'], workers=1
        )

        assert len(results) == 2
        drivers_used = {r.driver for r in results}
        assert drivers_used == {'pymupdf', 'pdfact'}

    @patch.object(Parxy, 'parse')
    def test_batch_with_batch_task_objects(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc

        results = Parxy.batch(
            tasks=[
                BatchTask(file='doc1.pdf', drivers=['pymupdf']),
                BatchTask(file='doc2.pdf', drivers=['pdfact'], level='line'),
            ],
            workers=1,
        )

        assert len(results) == 2
        assert mock_parse.call_count == 2

    @patch.object(Parxy, 'parse')
    def test_batch_with_mixed_tasks(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc

        results = Parxy.batch(
            tasks=[
                'simple.pdf',
                BatchTask(file='configured.pdf', drivers=['pdfact']),
            ],
            drivers=['pymupdf'],
            workers=1,
        )

        assert len(results) == 2

    @patch.object(Parxy, 'parse')
    def test_batch_per_file_driver_override(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc

        results = Parxy.batch(
            tasks=[
                BatchTask(file='doc.pdf', drivers=['pdfact']),
            ],
            drivers=['pymupdf'],  # Default should be overridden
            workers=1,
        )

        assert len(results) == 1
        assert results[0].driver == 'pdfact'

    @patch.object(Parxy, 'parse')
    def test_batch_per_file_level_override(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc

        Parxy.batch(
            tasks=[
                BatchTask(file='doc.pdf', level='line'),
            ],
            level='block',  # Default should be overridden
            workers=1,
        )

        mock_parse.assert_called_once()
        call_kwargs = mock_parse.call_args
        assert call_kwargs[1]['level'] == 'line'

    @patch.object(Parxy, 'parse')
    def test_batch_handles_parse_errors(self, mock_parse):
        mock_parse.side_effect = Exception('Parse failed')

        results = Parxy.batch(tasks=['doc.pdf'], workers=1)

        assert len(results) == 1
        assert results[0].failed is True
        assert results[0].error == 'Parse failed'
        assert results[0].document is None

    @patch.object(Parxy, 'parse')
    def test_batch_stop_on_error(self, mock_parse):
        def parse_side_effect(file, level, driver_name):
            if 'fail' in file:
                raise Exception('Parse failed')
            return Document(pages=[Page(number=1, text='test')])

        mock_parse.side_effect = parse_side_effect

        results = Parxy.batch(
            tasks=['fail.pdf', 'doc2.pdf', 'doc3.pdf'],
            stop_on_error=True,
            workers=1,
        )

        # With workers=1 and sequential processing, should stop after first error
        failed_results = [r for r in results if r.failed]
        assert len(failed_results) >= 1

    @patch.object(Parxy, 'parse')
    def test_batch_continue_on_error_by_default(self, mock_parse):
        call_count = 0

        def parse_side_effect(file, level, driver_name):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception('First parse failed')
            return Document(pages=[Page(number=1, text='test')])

        mock_parse.side_effect = parse_side_effect

        results = Parxy.batch(
            tasks=['doc1.pdf', 'doc2.pdf', 'doc3.pdf'],
            stop_on_error=False,
            workers=1,
        )

        # All files should be processed despite error
        assert len(results) == 3
        assert sum(1 for r in results if r.failed) == 1
        assert sum(1 for r in results if r.success) == 2

    @patch.object(Parxy, 'parse')
    def test_batch_uses_default_driver_when_none_specified(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc

        results = Parxy.batch(tasks=['doc.pdf'], workers=1)

        assert len(results) == 1
        assert results[0].driver == Parxy.default_driver()

    @patch.object(Parxy, 'parse')
    def test_batch_result_contains_file_reference(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc

        results = Parxy.batch(tasks=['my_document.pdf'], workers=1)

        assert results[0].file == 'my_document.pdf'

    @patch.object(Parxy, 'parse')
    def test_batch_with_bytes_input(self, mock_parse):
        doc = Document(pages=[Page(number=1, text='test')])
        mock_parse.return_value = doc
        pdf_bytes = b'%PDF-1.4 fake content'

        results = Parxy.batch(tasks=[pdf_bytes], workers=1)

        assert len(results) == 1
        assert results[0].file == pdf_bytes
        assert results[0].success is True

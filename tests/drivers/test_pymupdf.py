import os
import pytest

from parxy_core.models import TextBlock, Page

from parxy_core.drivers import PyMuPdfDriver
from parxy_core.exceptions import FileNotFoundException


class TestPymuPdfDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_pymupdf_driver_can_be_created(self):
        driver = PyMuPdfDriver()

        assert driver.supported_levels == ['page', 'block', 'line', 'span', 'character']

    def test_pymupdf_driver_unrecognized_level_handled(self):
        driver = PyMuPdfDriver()

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_pymupdf_driver_handle_not_existing_file(self):
        driver = PyMuPdfDriver()

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException) as excinfo:
            driver.parse(path)

    def test_pymupdf_driver_read_empty_document_block_level(self):
        driver = PyMuPdfDriver()

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path)

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is not None
        assert document.metadata.title
        assert document.metadata.title == 'Test document'
        assert document.metadata.author == 'Data House Author'
        assert document.metadata.subject == ''
        assert document.metadata.keywords == ''
        assert document.metadata.creator == 'Microsoft® Word for Microsoft 365'
        assert document.metadata.producer == 'Microsoft® Word for Microsoft 365'
        assert document.metadata.created_at == '2023-11-13T18:43:06'
        assert document.metadata.updated_at == document.metadata.created_at
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].text == '1 \n \n '
        assert len(document.pages[0].blocks) == 2
        assert isinstance(document.pages[0].blocks[0], TextBlock)

    def test_pymupdf_driver_read_empty_document_page_level(self):
        driver = PyMuPdfDriver()

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is not None
        assert document.metadata.title
        assert document.metadata.title == 'Test document'
        assert document.metadata.author == 'Data House Author'
        assert document.metadata.subject == ''
        assert document.metadata.keywords == ''
        assert document.metadata.creator == 'Microsoft® Word for Microsoft 365'
        assert document.metadata.producer == 'Microsoft® Word for Microsoft 365'
        assert document.metadata.created_at == '2023-11-13T18:43:06'
        assert document.metadata.updated_at == document.metadata.created_at
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].blocks is None
        assert document.pages[0].text == '1 \n \n '

    def test_pymupdf_driver_read_document(self):
        driver = PyMuPdfDriver()

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language is None
        assert document.outline is None
        assert document.metadata is not None
        assert document.metadata.title
        assert document.metadata.title == 'Test document'
        assert document.metadata.author == 'Data House Author'
        assert document.metadata.subject == ''
        assert document.metadata.keywords == ''
        assert document.metadata.creator == 'Microsoft® Word for Microsoft 365'
        assert document.metadata.producer == 'Microsoft® Word for Microsoft 365'
        assert document.metadata.created_at == '2023-05-09T11:34:41'
        assert document.metadata.updated_at == document.metadata.created_at
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].blocks is None
        assert (
            document.pages[0].text
            == 'This is the header \n \n1 \n \nThis is a test PDF to be used as input in unit \ntests \n \nThis is a heading 1 \nThis is a paragraph below heading 1 \n \n '
        )

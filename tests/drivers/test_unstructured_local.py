import os
import pytest

from parxy_core.exceptions import (
    FileNotFoundException,
)
from parxy_core.models import Page

from parxy_core.drivers import UnstructuredLocalDriver
from parxy_core.models import UnstructuredLocalConfig


class TestUnstructuredLocalDriver:
    def __fixture_path(self, file: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures_dir = os.path.join(os.path.dirname(current_dir), 'fixtures')
        return os.path.join(fixtures_dir, file)

    def test_unstructured_local_driver_can_be_created(self):
        driver = UnstructuredLocalDriver(UnstructuredLocalConfig().model_dump())

        assert driver.supported_levels == ['page', 'block']

    def test_unstructured_local_driver_handle_not_existing_file(self):
        driver = UnstructuredLocalDriver(UnstructuredLocalConfig().model_dump())

        path = self.__fixture_path('non-existing-file.pdf')

        with pytest.raises(FileNotFoundException) as excinfo:
            driver.parse(path)

    def test_unstructured_local_driver_unrecognized_level_handled(self):
        driver = UnstructuredLocalDriver(UnstructuredLocalConfig().model_dump())

        path = self.__fixture_path('empty-doc.pdf')

        with pytest.raises(ValueError) as excinfo:
            driver.parse(path, level='custom')

        assert 'not supported' in str(excinfo.value)
        assert '[custom]' in str(excinfo.value)

    def test_unstructured_local_driver_read_empty_document_page_level(self):
        driver = UnstructuredLocalDriver(UnstructuredLocalConfig().model_dump())

        path = self.__fixture_path('empty-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language == 'eng'
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert document.pages[0].text == '1'

    def test_unstructured_local_driver_read_document(self):
        driver = UnstructuredLocalDriver(UnstructuredLocalConfig().model_dump())

        path = self.__fixture_path('test-doc.pdf')
        document = driver.parse(path, level='page')

        assert document is not None
        assert document.language == 'eng'
        assert document.outline is None
        assert document.metadata is None
        assert len(document.pages) == 1
        assert isinstance(document.pages[0], Page)
        assert (
            document.pages[0].text
            == 'This is the header\nThis is a test PDF to be used as input in unit tests\nThis is a heading 1 This is a paragraph below heading 1\n1'
        )

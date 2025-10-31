import os
import pytest
import re

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
        assert document.pages[0].text == '1'

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
            == 'This is the header\n\n\nThis is a test PDF to be used as input in unit\ntests\n\n\n## This is a heading 1\nThis is a paragraph below heading 1\n\n\n1'
        )

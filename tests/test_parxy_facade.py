import pytest

from parxy_core.facade import Parxy
from parxy_core.drivers import DriverFactory
from parxy_core.drivers import Driver
from parxy_core.drivers import PyMuPdfDriver
from parxy_core.drivers import PdfActDriver
from parxy_core.drivers import LlamaParseDriver
from parxy_core.drivers import LlmWhispererDriver
from parxy_core.models import Document
from parxy_core.models import ParxyConfig


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

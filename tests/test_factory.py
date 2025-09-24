import pytest

from parxy_core.drivers import DriverFactory
from parxy_core.drivers import Driver
from parxy_core.drivers import PyMuPdfDriver
from parxy_core.drivers import PdfActDriver
from parxy_core.drivers import LlamaParseDriver
from parxy_core.drivers import LlmWhispererDriver
from parxy_core.drivers import UnstructuredLocalDriver
from parxy_core.models import Document
from parxy_core.models import ParxyConfig


class CustomDriverExample(Driver):
    """Example custom driver for testing."""
    supported_levels = ["page"]

    def _handle(self, file, level="page") -> Document:
        return Document(pages=[])


class TestDriverFactory:
    
    def test_build_required_to_create_instance(self):
        with pytest.raises(Exception) as excinfo:
            DriverFactory()
            
        assert "Use `DriverFactory.build()` to create an instance." in str(excinfo.value)
    
    def test_singleton(self):
        factory_one = DriverFactory.build()
        factory_two = DriverFactory.build()
            
        assert factory_one is factory_two
    
    def test_unrecognized_driver(self):
        with pytest.raises(ValueError) as excinfo:
            DriverFactory.build().driver('unrecognized')
            
        assert "Driver [unrecognized] not supported" in str(excinfo.value)

    def test_register_custom_driver(self):
        
        DriverFactory.build().forget_drivers().extend('custom', lambda: CustomDriverExample())
        
        driver = DriverFactory.build().driver('custom')
        
        document = driver.parse('example.pdf', level='page')

        assert isinstance(driver, CustomDriverExample)
        
        assert document is not None

        assert document.isEmpty()


    def test_no_duplicate_driver_can_be_registered(self):
        """Test that registering a duplicate driver name raises ValueError."""
        DriverFactory.build().forget_drivers().extend('custom', lambda: CustomDriverExample())
        
        with pytest.raises(ValueError) as excinfo:
            DriverFactory.build().extend('custom', lambda: CustomDriverExample())

        assert "Driver [custom] already registered" in str(excinfo.value)

    def test_default_driver_fallback_to_pymupdf(self):
        DriverFactory.reset()
        assert DriverFactory.build().default_driver_name() == 'pymupdf'

    def test_default_driver_name_read_from_configuration(self):
        DriverFactory.reset()
        assert DriverFactory.build().initialize(ParxyConfig(default_driver='pdfact')).default_driver_name() == 'pdfact'

    def test_default_driver_instantiated(self):
        DriverFactory.reset()
        driver = DriverFactory.build().driver()
        assert isinstance(driver, PyMuPdfDriver)

    def test_pymupdf_driver_instantiated(self):
        DriverFactory.reset()
        driver = DriverFactory.build().driver('pymupdf')
        assert isinstance(driver, PyMuPdfDriver)

    def test_pdfact_driver_instantiated(self):
        DriverFactory.reset()
        driver = DriverFactory.build().driver('pdfact')
        assert isinstance(driver, PdfActDriver)

    def test_llamaparse_driver_instantiated(self):
        DriverFactory.reset()
        driver = DriverFactory.build().driver('llamaparse')
        assert isinstance(driver, LlamaParseDriver)

    def test_llmwhisperer_driver_instantiated(self):
        DriverFactory.reset()
        driver = DriverFactory.build().driver('llmwhisperer')
        assert isinstance(driver, LlmWhispererDriver)

    def test_unstructured_local_driver_instantiated(self):
        DriverFactory.reset()
        driver = DriverFactory.build().driver('unstructured_local')
        assert isinstance(driver, UnstructuredLocalDriver)
import logging

from typing import Dict, Optional, Callable, Self, List

from parxy_core.drivers.abstract_driver import Driver
from parxy_core.drivers.pymupdf import PyMuPdfDriver
from parxy_core.drivers.pdfact import PdfActDriver
from parxy_core.drivers.llamaparse import LlamaParseDriver
from parxy_core.drivers.llmwhisperer import LlmWhispererDriver
from parxy_core.drivers.unstructured_local import UnstructuredLocalDriver
from parxy_core.models import (
    PdfActConfig,
    LlamaParseConfig,
    LlmWhispererConfig,
    UnstructuredLocalConfig,
    ParxyConfig,
)
from parxy_core.tracing import Tracer


class DriverFactory:
    """Factory class for managing document parser drivers.

    This factory manages the registration and instantiation of parser drivers.
    It supports both built-in drivers and custom driver registration.
    Each driver can be configured with specific settings during instantiation.

    This is a singleton class - only one instance will ever exist.
    Use DriverFactory.build() to get the instance.

    Example
    -------
    >>> factory = DriverFactory.build()
    >>> driver = factory.driver('pymupdf')
    """

    # Private class variable to hold the DriverFactory instance
    __instance: Optional['DriverFactory'] = None

    __drivers: Dict[str, Driver] = {}
    """The created drivers"""

    __custom_creators: Dict[str, Callable[[], Driver]] = {}
    """The custom drivers"""

    _config: Optional[ParxyConfig] = None

    _logger: logging.Logger = None

    def __init__(self):
        raise Exception('Use `DriverFactory.build()` to create an instance.')

    @classmethod
    def build(cls) -> 'DriverFactory':
        """Create a new factory instance.

        Returns
        -------
        DriverFactory
            The singleton instance of the factory.
        """
        if cls.__instance is None:
            cls.__instance = cls.__new__(cls).initialize(ParxyConfig())
        return cls.__instance

    @classmethod
    def reset(cls):
        cls.__instance = None

    def initialize(self, config: ParxyConfig) -> Self:
        self._config = config

        logger = logging.getLogger('parxy')

        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')

        if self._config.logging_file is not None:
            handler = logger.addHandler(
                logging.FileHandler(self._config.logging_file).setFormatter(formatter)
            )
        else:
            handler = logger.addHandler(logging.StreamHandler().setFormatter(formatter))

        logger.addHandler(handler)

        self._logger = logger

        self._tracer = Tracer(
            enabled=self._config.tracing_enabled, path=self._config.tracing_directory
        )

        return self

    def driver(self, name: str = None) -> Driver:
        """Get a driver instance.

        Parameters
        ----------
        name : str
            The name of the registered driver to instantiate

        Returns
        -------
        Driver
            A new instance of the requested driver

        Raises
        ------
        ValueError
            If driver is not registered
        """

        if name is None:
            name = self.default_driver_name()

        if name not in self.__drivers:
            self.__drivers[name] = self.__create_driver(name)

        return self.__drivers.get(name)

    def default_driver_name(self) -> str:
        return self._config.default_driver

    def __create_driver(self, name: str) -> Driver:
        """Create a new driver instance.

        Parameters
        ----------
        name : str
            The name of the registered driver to instantiate

        Returns
        -------
        Driver
            A new instance of the requested driver

        Raises
        ------
        ValueError
            If driver is not registered
        """

        if name in self.__custom_creators:
            return self.__custom_creators[name]()

        method_name = f'_create_{name}_driver'

        if hasattr(self, method_name):
            return getattr(self, method_name)()

        raise ValueError(f'Driver [{name}] not supported.')

    def _create_pymupdf_driver(self) -> PyMuPdfDriver:
        """Create a PyMuPDF Driver instance.

        Returns
        -------
        PyMuPdfDriver
            A new instance
        """
        return PyMuPdfDriver(logger=self._logger, tracer=self._tracer)

    def _create_pdfact_driver(self) -> PdfActDriver:
        """Create a PdfAct Driver instance.

        Returns
        -------
        PdfActDriver
            A new instance
        """
        return PdfActDriver(
            config=PdfActConfig().model_dump(), logger=self._logger, tracer=self._tracer
        )

    def _create_llamaparse_driver(self) -> LlamaParseDriver:
        """Create a LlamaParse Driver instance.

        Returns
        -------
        LlamaParseDriver
            A new instance
        """
        return LlamaParseDriver(
            config=LlamaParseConfig().model_dump(),
            logger=self._logger,
            tracer=self._tracer,
        )

    def _create_llmwhisperer_driver(self) -> LlmWhispererDriver:
        """Create a LlmWhisperer Driver instance.

        Returns
        -------
        LlmWhispererDriver
            A new instance
        """
        return LlmWhispererDriver(
            config=LlmWhispererConfig().model_dump(),
            logger=self._logger,
            tracer=self._tracer,
        )

    def _create_unstructured_local_driver(self) -> UnstructuredLocalDriver:
        """Create a Unstructured library (local installation via Python) Driver instance.

        Returns
        -------
        UnstructuredLocalDriver
            A new instance
        """
        return UnstructuredLocalDriver(
            config=UnstructuredLocalConfig().model_dump(),
            logger=self._logger,
            tracer=self._tracer,
        )

    def extend(self, name: str, callback: Callable[[], Driver]) -> 'DriverFactory':
        """Register a custom driver creator callable.

        Parameters
        ----------
        name : str
            The driver name
        callback : callable
            The function that creates the instance of the driver

        Raises
        ------
        ValueError
            If name is already registered
        """
        if name in self.__custom_creators:
            raise ValueError(f'Driver [{name}] already registered.')

        # TODO: pass logger and tracer to callback
        self.__custom_creators[name] = callback

        return self

    def get_drivers(self) -> Dict[str, Driver]:
        """Get all of the created "drivers".


        Returns
        -------
        Dict[str, Driver]
            The created driver instances
        """
        return self.__drivers

    def get_supported_drivers(self) -> List[str]:
        """Get the list of supported drivers.


        Returns
        -------
        List[str]
            The supported driver names
        """

        supported_drivers: List[str] = [
            'pymupdf',
            'pdfact',
            'llamaparse',
            'llmwhisperer',
            'unstructured_local',
        ]

        return supported_drivers

    def forget_drivers(self) -> 'DriverFactory':
        """Forget all instantiated and custom "drivers".


        Returns
        -------
        Dict[str, Driver]
            The created driver instances
        """

        self.__drivers = {}

        self.__custom_creators = {}

        return self

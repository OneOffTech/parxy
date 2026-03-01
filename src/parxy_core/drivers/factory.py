import importlib
import logging

from typing import Dict, Optional, Callable, Self, List, Union

from parxy_core.drivers.abstract_driver import Driver
from parxy_core.drivers.landingai import LandingAIADEDriver
from parxy_core.drivers.pymupdf import PyMuPdfDriver
from parxy_core.drivers.pdfact import PdfActDriver
from parxy_core.drivers.llamaparse import LlamaParseDriver
from parxy_core.drivers.llmwhisperer import LlmWhispererDriver
from parxy_core.drivers.unstructured_local import UnstructuredLocalDriver
from parxy_core.models import (
    PdfActConfig,
    LandingAIConfig,
    LlamaParseConfig,
    LlmWhispererConfig,
    UnstructuredLocalConfig,
    ParxyConfig,
)
from parxy_core.logging import create_isolated_logger
from parxy_core.tracing import tracer
from parxy_core.middleware import Middleware


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

    __middleware: List[Middleware] = []
    """The global middleware registry"""

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
        """Reset the factory instance and clear all state.

        This clears middleware, drivers, and custom creators.
        Useful for testing and isolation between test cases.
        """
        cls.__instance = None
        cls.__middleware = []
        cls.__drivers = {}
        cls.__custom_creators = {}

    def initialize(self, config: ParxyConfig) -> Self:
        self._config = config

        self._logger = create_isolated_logger(
            name='parxy',
            level=self._config.logging_level,
            add_console_handler=True,
            add_file_handler=True if self._config.logging_file is not None else False,
            file_path=self._config.logging_file,
        )

        # Configure tracing with the configuration
        tracer.configure(
            config=self._config,
            logger=self._logger,
            verbose=self._config.logging_level < logging.INFO
            or self._config.tracing.verbose,
        )

        # Load middleware from configuration
        self._load_middleware_from_config()

        return self

    def _load_middleware_from_config(self) -> None:
        """Load middleware from ParxyConfig.middleware.

        Middleware specified in config are automatically registered
        in the factory's global middleware registry.
        """
        if not self._config.middleware:
            return

        for middleware_path in self._config.middleware:
            try:
                middleware = self._import_middleware(middleware_path)
                self.__middleware.append(middleware)
                self._logger.info(f'Loaded middleware from config: {middleware_path}')
            except (ImportError, ValueError) as e:
                self._logger.warning(
                    f'Failed to load middleware from config: {middleware_path} - {e}'
                )

    def _import_middleware(self, middleware_path: str) -> Middleware:
        """Import a middleware class from a string path.

        Parameters
        ----------
        middleware_path : str
            Dot-notation path to the middleware class (e.g., 'parxy_core.middleware.PIIScanner')

        Returns
        -------
        Middleware
            An instance of the middleware class

        Raises
        ------
        ImportError
            If the module or class cannot be imported
        ValueError
            If the imported object is not a Middleware subclass
        """
        try:
            module_path, class_name = middleware_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            middleware_class = getattr(module, class_name)

            if not issubclass(middleware_class, Middleware):
                raise ValueError(f'{middleware_path} is not a Middleware subclass')

            return middleware_class()
        except (ImportError, AttributeError) as e:
            raise ImportError(f'Failed to import middleware: {middleware_path}') from e

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
        return PyMuPdfDriver(logger=self._logger)

    def _create_pdfact_driver(self) -> PdfActDriver:
        """Create a PdfAct Driver instance.

        Returns
        -------
        PdfActDriver
            A new instance
        """
        return PdfActDriver(config=PdfActConfig(), logger=self._logger)

    def _create_llamaparse_driver(self) -> LlamaParseDriver:
        """Create a LlamaParse Driver instance.

        Returns
        -------
        LlamaParseDriver
            A new instance
        """
        return LlamaParseDriver(
            config=LlamaParseConfig(),
            logger=self._logger,
        )

    def _create_llmwhisperer_driver(self) -> LlmWhispererDriver:
        """Create a LlmWhisperer Driver instance.

        Returns
        -------
        LlmWhispererDriver
            A new instance
        """
        return LlmWhispererDriver(
            config=LlmWhispererConfig(),
            logger=self._logger,
        )

    def _create_unstructured_local_driver(self) -> UnstructuredLocalDriver:
        """Create a Unstructured library (local installation via Python) Driver instance.

        Returns
        -------
        UnstructuredLocalDriver
            A new instance
        """
        return UnstructuredLocalDriver(
            config=UnstructuredLocalConfig(),
            logger=self._logger,
        )

    def _create_landingai_driver(self) -> LandingAIADEDriver:
        """Create a LandingAI ADE Driver instance.

        Returns
        -------
        LandingAIADEDriver
            A new instance
        """
        return LandingAIADEDriver(
            config=LandingAIConfig(),
            logger=self._logger,
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

        # TODO: pass logger to callback
        self.__custom_creators[name] = callback

        return self

    def with_middleware(
        self, middleware: Union[Middleware, List[Middleware]]
    ) -> 'DriverFactory':
        """Add middleware to the global middleware registry.

        Middleware added here will be applied to all drivers.

        Parameters
        ----------
        middleware : Union[Middleware, List[Middleware]]
            A middleware instance or list of middleware instances to add

        Returns
        -------
        DriverFactory
            Returns self for chaining

        Example
        -------
        >>> factory = DriverFactory.build()
        >>> factory.with_middleware([LoggingMiddleware(), PIIScannerMiddleware()])
        """
        if isinstance(middleware, list):
            self.__middleware.extend(middleware)
        else:
            self.__middleware.append(middleware)

        return self

    def clear_middleware(self) -> 'DriverFactory':
        """Clear all global middleware.

        Returns
        -------
        DriverFactory
            Returns self for chaining
        """
        self.__middleware.clear()

        return self

    def get_middleware(self) -> List[Middleware]:
        """Get the list of global middleware.

        Returns
        -------
        List[Middleware]
            Copy of the current global middleware list
        """
        return list(self.__middleware)

    def get_drivers(self) -> Dict[str, Driver]:
        """Get all of the created "drivers".


        Returns
        -------
        Dict[str, Driver]
            The created driver instances
        """
        return self.__drivers

    def get_config(self) -> ParxyConfig:
        """Get the Parxy configuration.

        Returns
        -------
        ParxyConfig
            The Parxy configuration
        """
        return self._config

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
            'landingai',
            'llamaparse',
            'llmwhisperer',
            'unstructured_local',
        ]

        return supported_drivers

    def get_custom_drivers(self) -> List[str]:
        """Get the list of custom registered drivers.

        Returns
        -------
        List[str]
            The custom driver names
        """
        return list(self.__custom_creators.keys())

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

"""Facade for accessing Parxy document parsing functionality."""

import io
from typing import Optional, Dict, Callable

from parxy_core.drivers import DriverFactory, Driver
from parxy_core.models import Document


class Parxy:
    """Static facade for accessing Parxy document processing features.

    This class provides a simplified interface to the document parsing functionality.
    It maintains a single DriverFactory instance and provides static methods for
    common operations like parsing documents and accessing specific drivers.

    Example
    -------
    Parse a document with default driver:
    >>> doc = Parxy.parse('path/to/document.pdf')

    Use a specific driver:
    >>> doc = Parxy.driver(Parxy.PYMUPDF).parse('path/to/document.pdf')

    """

    # Constants for common document processing drivers

    PYMUPDF = 'pymupdf'
    PDFACT = 'pdfact'
    LLAMAPARSE = 'llamaparse'
    LLMWHISPERER = 'llmwhisperer'
    UNSTRUCTURED_LIBRARY = 'unstructured_local'

    # Private class variable to hold the DriverFactory instance
    _factory: Optional[DriverFactory] = None

    def __new__(cls):
        """Prevent instantiation of this static class."""
        raise TypeError(f'{cls.__name__} is a static class and cannot be instantiated')

    @classmethod
    def _get_factory(cls) -> DriverFactory:
        """Get or create the DriverFactory instance.

        Returns
        -------
        DriverFactory
            The singleton instance of DriverFactory
        """
        if cls._factory is None:
            cls._factory = DriverFactory.build()
        return cls._factory

    @classmethod
    def parse(
        cls,
        file: str | io.BytesIO | bytes,
        level: str = 'block',
        driver_name: Optional[str] = None,
    ) -> Document:
        """Parse a document using the specified or default driver.

        Parameters
        ----------
        file : str | io.BytesIO | bytes
            The document to parse. Can be a file path, URL, or file-like object
        level : str, optional
            The level of detail for parsing, by default "block"
        driver_name : str, optional
            Name of the driver to use. If None, uses the default driver

        Returns
        -------
        Document
            The parsed document
        """
        return cls.driver(driver_name).parse(file=file, level=level)

    @classmethod
    def driver(cls, name: Optional[str] = None) -> Driver:
        """Get a driver instance by name.

        Parameters
        ----------
        name : str, optional
            Name of the driver to get. If None, returns the default driver

        Returns
        -------
        Driver
            The requested driver instance
        """
        return cls._get_factory().driver(name)

    @classmethod
    def drivers(cls) -> Dict[str, Driver]:
        """Get the list of supported drivers.

        Returns
        -------
        Driver
            The requested driver instance
        """
        return cls._get_factory().get_supported_drivers()

    @classmethod
    def extend(cls, name: str, callback: Callable[[], Driver]) -> 'DriverFactory':
        """Register a new driver with the factory.

        Parameters
        ----------
        name : str
            Name to register the driver under
        driver_class : type[Driver]
            The driver class to register
        config : Dict[str, Any], optional
            Initial configuration for the driver
        """
        return cls._get_factory().extend(name=name, callback=callback)

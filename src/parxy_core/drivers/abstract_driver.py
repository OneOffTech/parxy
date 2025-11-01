import io
import requests
import validators

from typing import Self
from abc import ABC, abstractmethod
from logging import Logger

from parxy_core.models import Document
from parxy_core.exceptions import (
    FileNotFoundException,
    ParsingException,
    AuthenticationException,
)
from parxy_core.models.config import BaseConfig
from parxy_core.logging import create_null_logger


class Driver(ABC):
    """Define a document processing driver.

    This class is intended to be abstract to serve as the starting point for implementing your own document processing

    Note to implementers:
    - Subclasses must implement the `_handle` method and declare the supported extraction levels.
    - If you need to initialize specific driver state override the _initialize method, as it will be called during class instantiation

    Attributes
    ----------
    supported_levels : list of str
        The list of supported extraction levels (e.g., `page`, `block`, `line`, etc.).

    _config : BaseConfig
        The configuration dictionary with specific parameters for initializing the document processing driver.

    _logger : Logger
        The logger instance.
    """

    supported_levels: list[str] = ['page', 'block']

    _config: BaseConfig

    _logger: Logger

    def __new__(
        cls, config: BaseConfig = None, logger: Logger = None
    ):
        instance = super().__new__(cls)
        instance.__init__(config=config, logger=logger)
        return instance

    def __init__(
        self, config: BaseConfig = None, logger: Logger = None
    ):
        self._config = config

        if logger is None:
            logger = create_null_logger(name=f'parxy.{self.__class__.__name__}')

        self._logger = logger
        self._initialize_driver()

    def parse(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'block',
        **kwargs,
    ) -> Document:
        """Parse a file

        Parameters
        ----
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Must be one of `supported_levels`. Default is `block`.
        **kwargs : dict
            Additional keyword arguments that can be passed to the specific driver.

        Returns
        -------
        Document
            A `Document` object representing the content.

        Throws
        -------
        ValueError
            If input is invalid, e.g. invalid URL, level

        FileNotFoundException
            If the file or URL is not accessible

        AuthenticationException
            In case authentication fails to third party service

        ParsingException
            For all unhandled exceptions during document processing
        """

        self._logger.debug(f'Parsing file using {self.__class__.__name__}', file)

        self._validate_level(level)

        try:
            document = self._handle(file=file, level=level, **kwargs)

            return document

        except Exception as ex:
            self._logger.error(
                f'Error while parsing file [{str(file)}]: {ex.message if hasattr(ex, "message") else str(ex)}',
                file,
                self.__class__.__name__,
                exc_info=True,
            )

            if isinstance(ex, FileNotFoundError):
                raise FileNotFoundException(ex, self.__class__) from ex
            elif isinstance(
                ex, (FileNotFoundException, AuthenticationException, ParsingException)
            ):
                raise ex
            raise ParsingException(ex, self.__class__) from ex

    def _initialize_driver(self) -> Self:
        """Initialize driver internal logic. It is called automatically during class initialization"""
        return self

    @abstractmethod
    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'block',
        **kwargs,
    ) -> Document:
        pass

    def _validate_level(self, level: str):
        if level not in self.supported_levels:
            raise ValueError(
                f'The level is not supported. Expected [{self.supported_levels}], received [{level}].'
            )

    @classmethod
    def get_stream_from_url(cls, url: str) -> io.BytesIO:
        if validators.url(url) is False:
            raise ValueError(f'The given input [`{url}`] is not a valid URL.')

        response = requests.get(url, stream=True)

        try:
            response.raise_for_status()
        except requests.HTTPError as hex:
            if hex.response.status_code in (401, 403):
                raise AuthenticationException(
                    f'Authentication error while downloading [{url}].', cls.__name__
                ) from hex
            elif hex.response.status_code == 404:
                raise FileNotFoundException(
                    f'File not found while downloading [{url}].', cls.__name__
                ) from hex

        file_input = io.BytesIO(response.content)
        file_input.name = url.split('/')[
            -1
        ]  # TODO: improve as some urls have accessible filename, others don't
        return file_input

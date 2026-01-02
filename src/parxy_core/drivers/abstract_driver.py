import base64
import hashlib
import io
import time
from abc import ABC, abstractmethod
from logging import Logger
from typing import Dict, Any, Self, Tuple, Optional

import requests
import validators

from parxy_core.models import Document
from parxy_core.exceptions import (
    FileNotFoundException,
    ParsingException,
    AuthenticationException,
)
from parxy_core.models.config import BaseConfig
from parxy_core.logging import create_null_logger
from parxy_core.tracing import tracer


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

    def __new__(cls, config: Dict[str, Any] = [], logger: Logger = None):
        instance = super().__new__(cls)
        instance.__init__(config=config, logger=logger)
        return instance

    def __init__(self, config: Dict[str, Any] = None, logger: Logger = None):
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

        with tracer.span(
            'document-processing',
            driver=self.__class__.__name__,
            level=level,
            **kwargs,
        ) as span:
            self._validate_level(level)

            try:
                # Start timing
                start_time = time.perf_counter()

                document = self._handle(file=file, level=level, **kwargs)

                # Calculate elapsed time in milliseconds
                end_time = time.perf_counter()
                elapsed_ms = (end_time - start_time) * 1000

                # Store elapsed time in parsing metadata
                if document.parsing_metadata is None:
                    document.parsing_metadata = {}
                document.parsing_metadata['driver_elapsed_time'] = elapsed_ms

                # Increment the documents processed counter
                tracer.count(
                    'documents.processed',
                    description='Total documents processed by each driver',
                    unit='documents',
                    driver=self.__class__.__name__,
                )

                return document

            except Exception as ex:
                self._logger.error(
                    'Error while parsing file',
                    file,
                    self.__class__.__name__,
                    exc_info=True,
                )

                tracer.count(
                    'documents.failures',
                    description='Failure during document processing by each driver',
                    unit='documents',
                    driver=self.__class__.__name__,
                )

                if isinstance(ex, FileNotFoundError):
                    parxy_exc = FileNotFoundException(ex, self.__class__)
                elif isinstance(
                    ex,
                    (FileNotFoundException, AuthenticationException, ParsingException),
                ):
                    parxy_exc = ex
                else:
                    parxy_exc = ParsingException(ex, self.__class__)
                tracer.error('Parsing failed', exception=str(parxy_exc))
                raise parxy_exc from ex

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

    def _trace_parse(self, filename: str, stream: bytes, **kwargs):
        """Create a tracing span for parsing operations with common attributes.

        This helper method reduces boilerplate in driver implementations by
        automatically adding common tracing attributes like file hash and
        driver information.

        Parameters
        ----------
        filename : str
            The name or path of the file being parsed
        stream : bytes
            The file content as bytes
        **kwargs : dict
            Additional keyword arguments passed to the driver

        Returns
        -------
        ContextManager[Span]
            A context manager yielding the OpenTelemetry span with common attributes pre-set

        Example
        -------
        >>> def _handle(self, file, level='block', **kwargs):
        ...     filename, stream = self.handle_file_input(file)
        ...     with self._trace_parse(filename, stream, **kwargs) as span:
        ...         result = do_parsing(stream)
        ...         tracer.info('Parsing complete', pages=len(result))
        ...     return convert_to_document(result)
        """
        return tracer.span(
            'parsing',
            file_name=filename,
            # file_stream=base64.b64encode(stream).decode('utf-8'),
            file_hash=self.hash_document(stream),
            file_size=len(stream),
            driver_class=self.__class__.__name__,
            **kwargs,
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

    @classmethod
    def handle_file_input(
        cls, file: str | io.BytesIO | bytes
    ) -> Tuple[Optional[str], bytes]:
        filename = ''
        if isinstance(file, str):
            filename = file
            if validators.url(file) is True:
                stream = Driver.get_stream_from_url(url=filename)
            else:
                with open(filename, 'rb') as filestream:
                    stream = filestream.read()
        elif isinstance(file, io.BytesIO):
            stream = file.read()
        elif isinstance(file, bytes):
            stream = file
        else:
            raise ValueError(
                'The given file is not supported. Expected `str` or bytes-like.'
            )
        return filename, stream

    @classmethod
    def hash_document(cls, stream: bytes) -> str:
        h = hashlib.new('sha256')
        h.update(stream)
        return h.hexdigest()

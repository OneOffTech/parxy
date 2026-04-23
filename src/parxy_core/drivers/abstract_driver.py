import hashlib
import io
import time
from abc import ABC, abstractmethod
from logging import Logger
from typing import Dict, Any, Self, Tuple, Optional, List, Union

import requests
import validators

from parxy_core.models import Document, ParsingRequest
from parxy_core.exceptions import (
    FileNotFoundException,
    ParsingException,
    AuthenticationException,
    RateLimitException,
    QuotaExceededException,
    InputValidationException,
)
from parxy_core.models.config import BaseConfig
from parxy_core.logging import create_null_logger
from parxy_core.tracing import tracer
from parxy_core.middleware import Middleware


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

    _middleware: List[Middleware]
    """Driver-specific middleware list"""

    def __new__(cls, config: Dict[str, Any] = [], logger: Logger = None):
        instance = super().__new__(cls)
        instance.__init__(config=config, logger=logger)
        return instance

    def __init__(self, config: Dict[str, Any] = None, logger: Logger = None):
        self._config = config

        if logger is None:
            logger = create_null_logger(name=f'parxy.{self.__class__.__name__}')

        self._logger = logger
        self._middleware = []  # Initialize empty middleware list
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

        self._logger.debug(
            f'Parsing file using {self.__class__.__name__}: {file if isinstance(file, str) else "stream"}'
        )

        with tracer.span(
            'document-processing',
            driver=self.__class__.__name__,
            level=level,
            **kwargs,
        ):
            self._validate_level(level)
            middleware_list = self._resolve_middleware()

            try:
                start_time = time.perf_counter()

                if middleware_list:
                    document = self._parse_with_middleware(
                        file=file,
                        level=level,
                        middleware_list=middleware_list,
                        **kwargs,
                    )
                else:
                    document = self._handle(file=file, level=level, **kwargs)

                end_time = time.perf_counter()
                elapsed_ms = (end_time - start_time) * 1000

                if document.parsing_metadata is None:
                    document.parsing_metadata = {}
                document.parsing_metadata['driver_elapsed_time'] = elapsed_ms

                tracer.count(
                    'documents.processed',
                    description='Total documents processed by each driver',
                    unit='documents',
                    driver=self.__class__.__name__,
                )

                return document

            except Exception as ex:
                self._logger.error(
                    f'Error while parsing file {file if isinstance(file, str) else "stream"} using {self.__class__.__name__}',
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
                    (
                        FileNotFoundException,
                        AuthenticationException,
                        ParsingException,
                        RateLimitException,
                        QuotaExceededException,
                        InputValidationException,
                    ),
                ):
                    parxy_exc = ex
                else:
                    parxy_exc = ParsingException(ex, self.__class__)
                tracer.error('Parsing failed', exception=str(parxy_exc))
                raise parxy_exc from ex

    def _resolve_middleware(self) -> List[Middleware]:
        """Resolve middleware for the current parse call.

        External middleware is applied first, then driver-specific middleware.
        """
        from parxy_core.drivers.factory import DriverFactory

        combined = DriverFactory.build().get_middleware()
        combined.extend(self._middleware)
        return combined

    def _parse_with_middleware(
        self,
        file: str | io.BytesIO | bytes,
        level: str,
        middleware_list: List[Middleware],
        **kwargs,
    ) -> Document:
        """Parse file with middleware chain.

        Parameters
        ----------
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str
            Desired extraction level.
        middleware_list : List[Middleware]
            List of middleware to apply.
        **kwargs : dict
            Additional keyword arguments.

        Returns
        -------
        Document
            The parsed document
        """
        # Create parsing request
        request = ParsingRequest(
            driver=self.__class__.__name__,
            file=file,
            level=level,
            config=kwargs,
        )

        with tracer.span('middleware-chain', count=len(middleware_list)):

            def call_handle(index: int, req: ParsingRequest) -> Document:
                if index >= len(middleware_list):
                    return self._handle(file=req.file, level=req.level, **req.config)

                current_middleware = middleware_list[index]
                with tracer.span(
                    'middleware.handle',
                    middleware=current_middleware.__class__.__name__,
                    index=index,
                ):
                    return current_middleware.handle(
                        req, lambda next_req: call_handle(index + 1, next_req)
                    )

            def call_terminate(index: int, doc: Document) -> Document:
                if index < 0:
                    return doc

                current_middleware = middleware_list[index]
                with tracer.span(
                    'middleware.terminate',
                    middleware=current_middleware.__class__.__name__,
                    index=index,
                ):
                    return current_middleware.terminate(
                        doc, lambda next_doc: call_terminate(index - 1, next_doc)
                    )

            document = call_handle(0, request)
            document = call_terminate(len(middleware_list) - 1, document)

        return document

    def _initialize_driver(self) -> Self:
        """Initialize driver internal logic. It is called automatically during class initialization"""
        return self

    def with_middleware(self, middleware: Union[Middleware, List[Middleware]]) -> Self:
        """Add middleware to this driver instance.

        Note: Drivers are singletons, so middleware added to a driver instance
        persists for all subsequent uses of that driver.

        Parameters
        ----------
        middleware : Union[Middleware, List[Middleware]]
            A middleware instance or list of middleware instances to add

        Returns
        -------
        Self
            Returns self for chaining

        Example
        -------
        >>> driver = Parxy.driver('pymupdf')
        >>> driver.with_middleware(LoggingMiddleware())
        >>> doc = driver.parse('document.pdf')
        """
        if isinstance(middleware, list):
            self._middleware.extend(middleware)
        else:
            self._middleware.append(middleware)
        return self

    def clear_middleware(self) -> Self:
        """Clear all middleware from this driver instance.

        Returns
        -------
        Self
            Returns self for chaining
        """
        self._middleware.clear()
        return self

    def get_middleware(self) -> List[Middleware]:
        """Get the list of middleware for this driver.

        Returns
        -------
        List[Middleware]
            Copy of the current middleware list
        """
        return list(self._middleware)

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

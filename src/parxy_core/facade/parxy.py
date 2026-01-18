"""Facade for accessing Parxy document parsing functionality."""

import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Callable, List, Union, Iterator

from parxy_core.drivers import DriverFactory, Driver
from parxy_core.models import Document, BatchTask, BatchResult
from parxy_core.models.config import ParxyConfig


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
        return (
            cls._get_factory().get_supported_drivers()
            + cls._get_factory().get_custom_drivers()
        )

    @classmethod
    def config(cls) -> ParxyConfig:
        """Get the Parxy configuration.

        Returns
        -------
        ParxyConfig
            The Parxy configuration
        """
        return cls._get_factory().get_config()

    @classmethod
    def default_driver(cls) -> str:
        """Get the configured default driver's name.

        Returns
        -------
        str
            The name of the default driver
        """
        return cls._get_factory().default_driver_name()

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

    @classmethod
    def batch_iter(
        cls,
        tasks: List[Union[BatchTask, str, io.BytesIO, bytes]],
        drivers: Optional[List[str]] = None,
        level: str = 'block',
        workers: Optional[int] = None,
    ) -> Iterator[BatchResult]:
        """Parse multiple documents in parallel, yielding results as they complete.

        This is the streaming version of batch(). Results are yielded as soon as
        each task completes, allowing for real-time progress updates.

        Parameters
        ----------
        tasks : List[BatchTask | str | io.BytesIO | bytes]
            List of tasks to process. Can be:
            - BatchTask objects with per-file configuration (drivers, level)
            - Simple file references (paths, URLs, or binary data)
        drivers : List[str], optional
            Default driver(s) to use when not specified in BatchTask.
            If None, uses the default driver
        level : str, optional
            Default extraction level when not specified in BatchTask,
            by default "block"
        workers : int, optional
            Number of parallel workers. Defaults to CPU count

        Yields
        ------
        BatchResult
            Results as they complete. Each result includes the file, driver used,
            parsed document (or None), and any error message.

        Example
        -------
        Stream results with real-time progress:

        >>> for result in Parxy.batch_iter(tasks=['doc1.pdf', 'doc2.pdf']):
        ...     if result.success:
        ...         print(f'{result.file} parsed with {result.driver}')
        ...     else:
        ...         print(f'{result.file} failed: {result.error}')

        Stop iteration on first error:

        >>> for result in Parxy.batch_iter(tasks=['doc1.pdf', 'doc2.pdf']):
        ...     if result.failed:
        ...         print(f'Stopping due to error: {result.error}')
        ...         break
        ...     process(result.document)
        """
        # Get default driver if none specified
        default_drivers = drivers if drivers else [cls.default_driver()]

        # Initialize factory before parallel execution to avoid
        # concurrent initialization of tracing/telemetry providers
        cls._get_factory()

        # Determine number of workers
        max_workers = workers if workers else (os.cpu_count() or 2)

        # Normalize tasks to BatchTask objects
        normalized_tasks: List[BatchTask] = []
        for task in tasks:
            if isinstance(task, BatchTask):
                normalized_tasks.append(task)
            else:
                # Simple file reference - wrap in BatchTask
                normalized_tasks.append(BatchTask(file=task))

        # Build list of (file, driver, level) work items
        work_items: List[tuple] = []
        for task in normalized_tasks:
            task_drivers = task.drivers if task.drivers else default_drivers
            task_level = task.level if task.level else level
            for driver_name in task_drivers:
                work_items.append((task.file, driver_name, task_level))

        def process_task(
            file: Union[str, io.BytesIO, bytes], driver_name: str, task_level: str
        ) -> BatchResult:
            try:
                doc = cls.parse(file=file, level=task_level, driver_name=driver_name)
                return BatchResult(
                    file=file, driver=driver_name, document=doc, error=None
                )
            except Exception as e:
                return BatchResult(
                    file=file, driver=driver_name, document=None, error=str(e)
                )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for file, driver_name, task_level in work_items:
                future = executor.submit(process_task, file, driver_name, task_level)
                futures.append(future)

            for future in as_completed(futures):
                yield future.result()

    @classmethod
    def batch(
        cls,
        tasks: List[Union[BatchTask, str, io.BytesIO, bytes]],
        drivers: Optional[List[str]] = None,
        level: str = 'block',
        workers: Optional[int] = None,
        stop_on_error: bool = False,
    ) -> List[BatchResult]:
        """Parse multiple documents in parallel using specified drivers.

        Accepts either a list of BatchTask objects for per-file configuration,
        or a simple list of files with shared configuration. For streaming results
        as they complete, use batch_iter() instead.

        Parameters
        ----------
        tasks : List[BatchTask | str | io.BytesIO | bytes]
            List of tasks to process. Can be:
            - BatchTask objects with per-file configuration (drivers, level)
            - Simple file references (paths, URLs, or binary data)
        drivers : List[str], optional
            Default driver(s) to use when not specified in BatchTask.
            If None, uses the default driver
        level : str, optional
            Default extraction level when not specified in BatchTask,
            by default "block"
        workers : int, optional
            Number of parallel workers. Defaults to CPU count
        stop_on_error : bool, optional
            If True, stop processing immediately when the first error occurs.
            Pending tasks will be cancelled. By default False

        Returns
        -------
        List[BatchResult]
            List of BatchResult objects containing the parsing results.
            Each result includes the file, driver used, parsed document (or None),
            and any error message. Results are returned in completion order.
            If stop_on_error is True and an error occurs, only results
            completed before the error (plus the error itself) are returned.

        Example
        -------
        Simple mode with shared configuration:

        >>> results = Parxy.batch(
        ...     tasks=['doc1.pdf', 'doc2.pdf'],
        ...     drivers=['pymupdf', 'llamaparse'],
        ...     workers=4,
        ... )

        Advanced mode with per-file configuration:

        >>> results = Parxy.batch(
        ...     tasks=[
        ...         BatchTask(file='simple.pdf'),  # Uses defaults
        ...         BatchTask(file='complex.pdf', drivers=['llamaparse'], level='line'),
        ...         BatchTask(file=pdf_bytes, drivers=['pymupdf', 'pdfact']),
        ...     ],
        ...     drivers=['pymupdf'],  # Default for tasks without drivers
        ...     level='block',  # Default for tasks without level
        ... )
        >>> for result in results:
        ...     if result.success:
        ...         print(f'{result.file} parsed with {result.driver}')
        ...     else:
        ...         print(f'{result.file} failed: {result.error}')

        Stop on first error:

        >>> results = Parxy.batch(
        ...     tasks=['doc1.pdf', 'doc2.pdf'],
        ...     stop_on_error=True,
        ... )
        """
        results: List[BatchResult] = []

        for result in cls.batch_iter(
            tasks=tasks,
            drivers=drivers,
            level=level,
            workers=workers,
        ):
            results.append(result)

            if stop_on_error and result.failed:
                break

        return results

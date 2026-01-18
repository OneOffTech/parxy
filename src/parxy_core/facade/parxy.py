"""Facade for accessing Parxy document parsing functionality."""

import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Callable, List, Union, Iterator

from pathlib import Path

from parxy_core.drivers import DriverFactory, Driver
from parxy_core.models import Document, BatchTask, BatchResult
from parxy_core.models.config import ParxyConfig
from parxy_core.services.pdf_service import PdfService


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

    # ========================================================================
    # PDF Manipulation Namespace
    # ========================================================================

    class pdf:
        """PDF manipulation operations namespace.

        Provides static methods for PDF operations like merging, splitting,
        and optimizing PDFs.

        Example
        -------
        >>> Parxy.pdf.merge([(Path('doc1.pdf'), None, None)], Path('out.pdf'))
        >>> Parxy.pdf.split(Path('doc.pdf'), Path('./pages'), 'doc')
        >>> Parxy.pdf.optimize(Path('large.pdf'), Path('small.pdf'))
        """

        def __new__(cls):
            """Prevent instantiation of this static class."""
            raise TypeError(
                f'{cls.__name__} is a static class and cannot be instantiated'
            )

        @staticmethod
        def merge(
            inputs: List[tuple[Path, Optional[int], Optional[int]]],
            output: Path,
        ) -> None:
            """Merge multiple PDF files into a single PDF.

            Parameters
            ----------
            inputs : List[tuple[Path, Optional[int], Optional[int]]]
                List of tuples (pdf_path, from_page, to_page) where
                page numbers are 0-based. None means all pages or last page.
            output : Path
                Path where the merged PDF should be saved

            Raises
            ------
            FileNotFoundError
                If any input PDF doesn't exist
            ValueError
                If page ranges are invalid

            Example
            -------
            Merge two complete PDFs:

            >>> Parxy.pdf.merge(
            ...     [(Path('doc1.pdf'), None, None), (Path('doc2.pdf'), None, None)],
            ...     Path('merged.pdf')
            ... )

            Merge specific page ranges:

            >>> Parxy.pdf.merge(
            ...     [(Path('doc1.pdf'), 0, 2), (Path('doc2.pdf'), 0, 0)],
            ...     Path('selected.pdf')
            ... )
            """
            PdfService.merge_pdfs(inputs, output)

        @staticmethod
        def split(
            input_path: Path,
            output_dir: Path,
            prefix: str,
        ) -> List[Path]:
            """Split a PDF file into individual pages.

            Parameters
            ----------
            input_path : Path
                Path to the PDF file to split
            output_dir : Path
                Directory where split PDFs should be saved
            prefix : str
                Prefix for output filenames

            Returns
            -------
            List[Path]
                List of paths to the created PDF files

            Raises
            ------
            FileNotFoundError
                If input PDF doesn't exist
            ValueError
                If PDF is empty or invalid

            Example
            -------
            Split a PDF into individual pages:

            >>> pages = Parxy.pdf.split(
            ...     Path('document.pdf'),
            ...     Path('./pages'),
            ...     'doc'
            ... )
            >>> print(pages)
            [Path('pages/doc_page_1.pdf'), Path('pages/doc_page_2.pdf'), ...]
            """
            return PdfService.split_pdf(input_path, output_dir, prefix)

        @staticmethod
        def optimize(
            input_path: Path,
            output_path: Path,
            scrub_metadata: bool = True,
            subset_fonts: bool = True,
            compress_images: bool = True,
            dpi_threshold: int = 100,
            dpi_target: int = 72,
            image_quality: int = 60,
            convert_to_grayscale: bool = False,
        ) -> Dict[str, any]:
            """Optimize PDF file size using compression techniques.

            This method applies three optimization techniques:
            1. Dead-weight removal - Removes metadata, thumbnails, embedded files
            2. Font subsetting - Keeps only used glyphs from embedded fonts
            3. Image compression - Downsamples and compresses images

            Parameters
            ----------
            input_path : Path
                Path to the input PDF file
            output_path : Path
                Path where optimized PDF should be saved
            scrub_metadata : bool, optional
                Remove metadata, thumbnails, and embedded files, by default True
            subset_fonts : bool, optional
                Subset embedded fonts to only used glyphs, by default True
            compress_images : bool, optional
                Apply image compression and downsampling, by default True
            dpi_threshold : int, optional
                Only process images above this DPI, by default 100
            dpi_target : int, optional
                Target DPI for downsampling, by default 72
            image_quality : int, optional
                JPEG quality level 0-100, by default 60
            convert_to_grayscale : bool, optional
                Convert images to grayscale, by default False

            Returns
            -------
            Dict[str, any]
                Dictionary with optimization results:
                - original_size: Original file size in bytes
                - optimized_size: Optimized file size in bytes
                - reduction_bytes: Size reduction in bytes
                - reduction_percent: Size reduction as percentage

            Raises
            ------
            FileNotFoundError
                If input PDF doesn't exist
            ValueError
                If parameters are invalid

            Example
            -------
            Optimize a PDF with default settings:

            >>> result = Parxy.pdf.optimize(
            ...     Path('large.pdf'),
            ...     Path('optimized.pdf')
            ... )
            >>> print(f"Reduced by {result['reduction_percent']:.1f}%")
            """
            return PdfService.optimize_pdf(
                input_path=input_path,
                output_path=output_path,
                scrub_metadata=scrub_metadata,
                subset_fonts=subset_fonts,
                compress_images=compress_images,
                dpi_threshold=dpi_threshold,
                dpi_target=dpi_target,
                image_quality=image_quality,
                convert_to_grayscale=convert_to_grayscale,
            )

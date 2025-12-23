"""Docling backend driver for parxy.

IBM Docling provides high-quality PDF to markdown conversion with
optional OCR support and table structure extraction.

IMPORTANT - Resource Requirements:
    - Fast mode (no OCR): ~8-12GB RAM per instance, ~2-5 sec/doc
    - Accurate mode (with OCR): ~12-16GB RAM per instance, ~30-60 sec/doc
    - GPU recommended for OCR mode (CUDA or MPS)
    - KNOWN MEMORY LEAK: Docling accumulates memory over conversions
      (see https://github.com/docling-project/docling/issues/2209)

Configuration:
    Environment variables: PARXY_DOCLING_DO_OCR=true, etc.
    Config file: .env file with parxy_docling_ prefix

Example .env configuration:
    PARXY_DOCLING_DO_OCR=false
    PARXY_DOCLING_DO_TABLE_STRUCTURE=true
    PARXY_DOCLING_NUM_THREADS=2
    PARXY_DOCLING_DEVICE=auto
"""

import gc
import io
import os
import tempfile

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page

# Set thread limits BEFORE importing docling (affects MKL, OpenMP, etc.)
# See: https://github.com/docling-project/docling-serve/issues/366
_num_threads = os.environ.get('PARXY_DOCLING_NUM_THREADS', '2')
os.environ.setdefault('OMP_NUM_THREADS', _num_threads)
os.environ.setdefault('MKL_NUM_THREADS', _num_threads)
os.environ.setdefault('OPENBLAS_NUM_THREADS', _num_threads)

# Recreate converter every N documents to mitigate memory leaks
# See: https://github.com/docling-project/docling/issues/2209
CONVERTER_RESET_INTERVAL = 10


class DoclingBackend(Driver):
    """PDF parser using IBM Docling - highest quality extraction.

    Docling uses deep learning models for document understanding.
    Best quality output but requires significant resources.

    By default, OCR is DISABLED for performance. Enable via:
        - Environment: PARXY_DOCLING_DO_OCR=true
        - Config file: parxy_docling_do_ocr=true in .env

    Resource estimates:
        - Fast mode (no OCR): 2-4GB RAM, 2-5 sec/doc
        - Accurate mode (OCR): 8-12GB RAM, 30-60 sec/doc, GPU recommended
    """

    supported_levels = ['page']

    def _initialize_driver(self):
        """Initialize Docling driver and check dependencies."""
        try:
            import docling  # noqa: F401
        except ImportError as e:
            raise ImportError(
                'docling is required. Install with: pip install parxy[docling]'
            ) from e

        # Extract configuration from config object
        if self._config:
            self._do_ocr = getattr(self._config, 'do_ocr', False)
            self._do_table_structure = getattr(self._config, 'do_table_structure', True)
            self._num_threads = getattr(self._config, 'num_threads', 2)
            self._device = getattr(self._config, 'device', 'auto')
            self._generate_page_images = getattr(
                self._config, 'generate_page_images', False
            )
            self._generate_picture_images = getattr(
                self._config, 'generate_picture_images', False
            )
            self._images_scale = getattr(self._config, 'images_scale', None)
        else:
            # Defaults if no config provided
            self._do_ocr = False
            self._do_table_structure = True
            self._num_threads = 2
            self._device = 'auto'
            self._generate_page_images = False
            self._generate_picture_images = False
            self._images_scale = None

        # Lazy-loaded converter (created on first use)
        self._converter = None
        # Counter for memory leak mitigation
        self._conversion_count = 0

        return self

    def _get_converter(self):
        """Get or create the document converter with configured options."""
        if self._converter is not None:
            return self._converter

        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        # Configure pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = self._do_ocr
        pipeline_options.do_table_structure = self._do_table_structure

        # Configure additional options
        if self._generate_page_images:
            pipeline_options.generate_page_images = True
        if self._generate_picture_images:
            pipeline_options.generate_picture_images = True
        if self._images_scale:
            pipeline_options.images_scale = float(self._images_scale)

        # Configure accelerator options
        try:
            from docling.datamodel.accelerator_options import (
                AcceleratorDevice,
                AcceleratorOptions,
            )

            device_map = {
                'auto': AcceleratorDevice.AUTO,
                'cpu': AcceleratorDevice.CPU,
                'cuda': AcceleratorDevice.CUDA,
                'mps': AcceleratorDevice.MPS,
            }
            device = device_map.get(self._device.lower(), AcceleratorDevice.AUTO)

            pipeline_options.accelerator_options = AcceleratorOptions(
                num_threads=self._num_threads,
                device=device,
            )
        except ImportError:
            pass  # Older docling version

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        return self._converter

    def _handle(
        self, file: str | io.BytesIO | bytes, level: str = 'page', **kwargs
    ) -> Document:
        """Parse PDF to Document object.

        Includes memory cleanup to mitigate known docling memory leaks.
        See: https://github.com/docling-project/docling/issues/2209

        Parameters
        ----------
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Default is "page".
        **kwargs : dict
            Additional keyword arguments.

        Returns
        -------
        Document
            A parsed Document in unified format with markdown content.
        """
        filename, stream = self.handle_file_input(file)

        # Reset converter periodically to mitigate memory leaks
        if self._conversion_count >= CONVERTER_RESET_INTERVAL:
            self._converter = None
            gc.collect()
            self._conversion_count = 0

        with self._trace_parse(filename, stream, **kwargs) as span:
            converter = self._get_converter()

            # Docling requires a file path, so write to temp file if needed
            if isinstance(file, str) and not file.startswith(('http://', 'https://')):
                # Use the original file path directly
                result = converter.convert(file)
            else:
                # Write stream to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(stream)
                    tmp_path = tmp.name

                try:
                    result = converter.convert(tmp_path)
                finally:
                    os.unlink(tmp_path)

            markdown_text = result.document.export_to_markdown()

            # Memory cleanup: call unload() on backends to release resources
            # See: https://github.com/docling-project/docling-serve/issues/366
            try:
                # Primary cleanup path: result.input._backend.unload()
                if hasattr(result, 'input') and hasattr(result.input, '_backend'):
                    backend = result.input._backend
                    if hasattr(backend, 'unload'):
                        backend.unload()
                # Fallback: try document._backend
                elif hasattr(result, 'document') and hasattr(
                    result.document, '_backend'
                ):
                    backend = result.document._backend
                    if hasattr(backend, 'unload'):
                        backend.unload()
                # Also try result-level unload
                if hasattr(result, 'unload'):
                    result.unload()
            except Exception:
                pass  # Best effort cleanup

            self._conversion_count += 1
            gc.collect()

            # Create a single page with the markdown content
            pages = [
                Page(
                    number=0,
                    text=markdown_text,
                    blocks=None,
                )
            ]

            span.set_attribute('output.pages', len(pages))

        return Document(
            filename=filename,
            pages=pages,
        )

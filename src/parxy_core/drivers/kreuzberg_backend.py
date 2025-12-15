"""Kreuzberg backend driver for parxy.

NOTE: By default, this backend disables OCR to avoid loading heavy ML models.
For OCR-based extraction, use force_ocr=True in the driver configuration.

IMPORTANT: OCR requires the tesseract-ocr system package to be installed:
    Ubuntu/Debian: sudo apt-get install tesseract-ocr
    macOS: brew install tesseract
    Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
"""

import asyncio
import io
import tempfile

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page


class KreuzbergBackend(Driver):
    """PDF parser using Kreuzberg - fast Rust-based extraction.

    Kreuzberg is a high-performance document extraction library with
    a Rust core. Fast, lightweight, with built-in OCR support.

    By default, OCR is disabled for performance. Enable with force_ocr=True.
    """

    supported_levels = ["page"]

    def _initialize_driver(self):
        """Initialize Kreuzberg driver by checking if the library is available."""
        try:
            from kreuzberg import ExtractionConfig, extract_file  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "kreuzberg is required. Install with: pip install parxy[kreuzberg]"
            ) from e

        # Get OCR setting from config if available
        self._force_ocr = False
        if self._config and hasattr(self._config, "force_ocr"):
            self._force_ocr = self._config.force_ocr

        return self

    def _handle(
        self, file: str | io.BytesIO | bytes, level: str = "page", **kwargs
    ) -> Document:
        """Parse PDF to Document object.

        Parameters
        ----------
        file : str | io.BytesIO | bytes
            Path, URL or stream of the file to parse.
        level : str, optional
            Desired extraction level. Default is "page".
        **kwargs : dict
            Additional keyword arguments. Can include 'force_ocr' to enable OCR.

        Returns
        -------
        Document
            A parsed Document in unified format.
        """
        # Kreuzberg is async, so we need to run it in an event loop
        return asyncio.run(self._handle_async(file, level, **kwargs))

    async def _handle_async(
        self, file: str | io.BytesIO | bytes, level: str = "page", **kwargs
    ) -> Document:
        """Async implementation of PDF parsing.

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
            A parsed Document in unified format.
        """
        from kreuzberg import ExtractionConfig, extract_file

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            # Get OCR setting from kwargs or instance config
            force_ocr = kwargs.get("force_ocr", self._force_ocr)

            # Create extraction config
            if force_ocr:
                config = ExtractionConfig(force_ocr=True)
            else:
                # Text-only mode: no OCR backend, much faster and lighter
                config = ExtractionConfig(ocr_backend=None, force_ocr=False)

            # Kreuzberg requires a file path, so write to temp file if needed
            if isinstance(file, str) and not file.startswith(("http://", "https://")):
                # Use the original file path directly
                result = await extract_file(file, config=config)
            else:
                # Write stream to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(stream)
                    tmp_path = tmp.name

                try:
                    result = await extract_file(tmp_path, config=config)
                finally:
                    import os
                    os.unlink(tmp_path)

            markdown_text = result.content

            # Create a single page with the markdown content
            pages = [
                Page(
                    number=0,
                    text=markdown_text,
                    blocks=None,
                )
            ]

            span.set_attribute("output.pages", len(pages))

        return Document(
            filename=filename,
            pages=pages,
        )

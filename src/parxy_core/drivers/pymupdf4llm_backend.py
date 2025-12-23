"""PyMuPDF4LLM backend driver for parxy."""

import io

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page


class PyMuPDF4LLMBackend(Driver):
    """PDF parser using PyMuPDF4LLM - optimized for LLM consumption.

    PyMuPDF4LLM builds on PyMuPDF to produce markdown output specifically
    formatted for LLM processing. Good balance of quality and speed.
    """

    supported_levels = ['page']

    def _initialize_driver(self):
        """Initialize PyMuPDF4LLM driver by checking if the library is available."""
        try:
            import pymupdf4llm  # noqa: F401
        except ImportError as e:
            raise ImportError(
                'pymupdf4llm is required. Install with: pip install parxy[light]'
            ) from e
        return self

    def _handle(
        self, file: str | io.BytesIO | bytes, level: str = 'page', **kwargs
    ) -> Document:
        """Parse PDF to Document object.

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
        import pymupdf4llm
        import tempfile

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            # PyMuPDF4LLM requires a file path, so write to temp file if needed
            if isinstance(file, str) and not file.startswith(('http://', 'https://')):
                # Use the original file path directly
                markdown_text = pymupdf4llm.to_markdown(file)
            else:
                # Write stream to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(stream)
                    tmp_path = tmp.name

                try:
                    markdown_text = pymupdf4llm.to_markdown(tmp_path)
                finally:
                    import os

                    os.unlink(tmp_path)

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

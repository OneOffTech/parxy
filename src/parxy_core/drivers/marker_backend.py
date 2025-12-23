"""Marker backend driver for parxy."""

import io
import tempfile

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page


class MarkerBackend(Driver):
    """PDF parser using Marker - deep learning for academic PDFs.

    Marker uses deep learning models optimized for academic papers
    and technical documents. Excellent for LaTeX-heavy content.
    """

    supported_levels = ['page']

    def _initialize_driver(self):
        """Initialize Marker driver and load ML models."""
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
        except ImportError as e:
            raise ImportError(
                'marker-pdf is required. Install with: pip install parxy[marker]'
            ) from e

        # Load models
        self._models = create_model_dict()
        self._converter = PdfConverter(artifact_dict=self._models)
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
        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            # Marker requires a file path, so write to temp file if needed
            if isinstance(file, str) and not file.startswith(('http://', 'https://')):
                # Use the original file path directly
                result = self._converter(file)
            else:
                # Write stream to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(stream)
                    tmp_path = tmp.name

                try:
                    result = self._converter(tmp_path)
                finally:
                    import os

                    os.unlink(tmp_path)

            markdown_text = result.markdown

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

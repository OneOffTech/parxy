"""PDFMiner backend driver for parxy."""

import io

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page


class PDFMinerBackend(Driver):
    """PDF parser using PDFMiner - mature text extraction.

    PDFMiner is a mature, pure-Python PDF text extraction library.
    Good for text-heavy documents, handles various encodings well.
    """

    supported_levels = ["page"]

    def _initialize_driver(self):
        """Initialize PDFMiner driver by checking if the library is available."""
        try:
            from pdfminer.high_level import extract_text_to_fp  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "pdfminer.six is required. Install with: pip install parxy[pdfminer]"
            ) from e
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
            Additional keyword arguments.

        Returns
        -------
        Document
            A parsed Document in unified format.
        """
        from io import StringIO
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            output = StringIO()
            stream_io = io.BytesIO(stream)
            extract_text_to_fp(stream_io, output, laparams=LAParams())
            text = output.getvalue().strip()

            # Create a single page with the extracted text
            pages = [
                Page(
                    number=0,
                    text=text,
                    blocks=None,
                )
            ]

            span.set_attribute("output.pages", len(pages))

        return Document(
            filename=filename,
            pages=pages,
        )

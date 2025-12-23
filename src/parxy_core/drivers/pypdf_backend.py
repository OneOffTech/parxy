"""PyPDF backend driver for parxy."""

import io

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page


class PyPDFBackend(Driver):
    """PDF parser using PyPDF for text extraction.

    PyPDF is a pure-python library - lightweight with no binary dependencies.
    Good for simple text extraction, not ideal for complex layouts or tables.
    """

    supported_levels = ['page']

    def _initialize_driver(self):
        """Initialize PyPDF driver by checking if the library is available."""
        try:
            import pypdf  # noqa: F401
        except ImportError as e:
            raise ImportError(
                'pypdf is required. Install with: pip install parxy[pypdf]'
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
            A parsed Document in unified format.
        """
        from pypdf import PdfReader

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            reader = PdfReader(io.BytesIO(stream))

            pages = []
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages.append(
                        Page(
                            number=page_num,
                            text=text.strip(),
                            blocks=None,
                        )
                    )
                else:
                    # Include empty pages to maintain page numbering
                    pages.append(
                        Page(
                            number=page_num,
                            text='',
                            blocks=None,
                        )
                    )

            span.set_attribute('output.pages', len(pages))

        return Document(
            filename=filename,
            pages=pages,
        )

"""PyPDFium2 backend driver for parxy."""

import io

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page


class PyPDFium2Backend(Driver):
    """PDF parser using PyPDFium2 - Chrome's PDF engine.

    PyPDFium2 wraps PDFium, the PDF rendering engine used in Chrome.
    Fast and reliable for text extraction.
    """

    supported_levels = ['page']

    def _initialize_driver(self):
        """Initialize PyPDFium2 driver by checking if the library is available."""
        try:
            import pypdfium2  # noqa: F401
        except ImportError as e:
            raise ImportError(
                'pypdfium2 is required. Install with: pip install parxy[pypdfium2]'
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
        import pypdfium2 as pdfium

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            pdf = pdfium.PdfDocument(stream)

            pages = []
            for page_num, page in enumerate(pdf):
                textpage = page.get_textpage()
                text = textpage.get_text_range()
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

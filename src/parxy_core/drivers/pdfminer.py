"""PDFMiner driver for parxy."""

import io

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page


class PDFMinerDriver(Driver):
    """PDF parser using PDFMiner - mature text extraction.

    PDFMiner is a mature, pure-Python PDF text extraction library.
    Good for text-heavy documents, handles various encodings well.
    """

    supported_levels = ['page', 'block']

    def _initialize_driver(self):
        """Initialize PDFMiner driver by checking if the library is available."""
        try:
            from pdfminer.high_level import extract_pages  # noqa: F401
        except ImportError as e:
            raise ImportError(
                'pdfminer.six is required. Install with: pip install parxy[pdfminer]'
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
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LAParams, LTTextContainer

        if level == 'block':
            level = 'page'

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            pages = []
            for page_num, page_layout in enumerate(
                extract_pages(io.BytesIO(stream), laparams=LAParams()), start=1
            ):
                text = ''.join(
                    element.get_text()
                    for element in page_layout
                    if isinstance(element, LTTextContainer)
                ).strip()
                pages.append(Page(number=page_num, text=text, blocks=None))

            span.set_attribute('output.pages', len(pages))

        return Document(
            filename=filename,
            pages=pages,
        )

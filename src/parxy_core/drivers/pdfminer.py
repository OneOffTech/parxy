"""PDFMiner driver for parxy."""

import io
from typing import Any, Optional

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page, TocEntry


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
        from pdfminer.pdfdocument import PDFDocument, PDFNoOutlines
        from pdfminer.pdfpage import PDFPage, LITERAL_PAGE
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdftypes import PDFObjRef

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

            outline = None
            parser = PDFParser(io.BytesIO(stream))
            try:
                doc = PDFDocument(parser)
                resolver = _PageNumberResolver(doc, PDFPage, LITERAL_PAGE, PDFObjRef)
                entries = []
                for bm_level, title, dest, a, se in doc.get_outlines():
                    ref = dest if dest is not None else (a if a is not None else se)
                    page_num = resolver.resolve(ref) if ref is not None else None
                    entries.append(
                        TocEntry(
                            title=title,
                            page=page_num,
                            level=bm_level,
                        )
                    )
                if entries:
                    outline = entries
            except PDFNoOutlines:
                pass
            finally:
                parser.flush()

        return Document(
            filename=filename,
            pages=pages,
            outline=outline,
        )


class _PageNumberResolver:
    """Resolves PDF destination references to 1-based page numbers."""

    def __init__(self, document: Any, PDFPage: Any, LITERAL_PAGE: Any, PDFObjRef: Any):
        self._document = document
        self._LITERAL_PAGE = LITERAL_PAGE
        self._PDFObjRef = PDFObjRef
        self._objid_to_pagenum: dict[int, int] = {
            page.pageid: page_num
            for page_num, page in enumerate(PDFPage.create_pages(document), 1)
        }

    def resolve(self, ref: Any) -> Optional[int]:
        if isinstance(ref, self._PDFObjRef):
            resolved = ref.resolve()
            if (
                isinstance(resolved, dict)
                and resolved.get('Type') is self._LITERAL_PAGE
            ):
                return self._objid_to_pagenum.get(ref.objid)
            return self.resolve(resolved)
        if isinstance(ref, dict) and 'D' in ref:
            return self.resolve(ref['D'])
        if isinstance(ref, list):
            first_ref = next((e for e in ref if isinstance(e, self._PDFObjRef)), None)
            if first_ref is not None:
                return self.resolve(first_ref)
        if isinstance(ref, bytes):
            return self.resolve(self._document.get_dest(ref))
        return None

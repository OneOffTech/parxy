"""PyPDFium2 driver for parxy."""

import io

from datetime import datetime

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page, Metadata


class PyPDFium2Driver(Driver):
    """PDF parser using PyPDFium2 - Chrome's PDF engine.

    PyPDFium2 wraps PDFium, the PDF rendering engine used in Chrome.
    Fast and reliable for text extraction.

    Thread-safety: PDFium is not thread-safe and in practice crashes even
    when calls are serialized via a lock or routed through a dedicated
    single-thread executor. Batch processing with this driver must be run
    with a single worker; ``Parxy.batch_iter`` enforces this automatically.
    """

    supported_levels = ["page", "block"]

    def _initialize_driver(self):
        """Initialize PyPDFium2 driver by checking if the library is available."""
        try:
            import pypdfium2  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "pypdfium2 is required. Install with: pip install parxy[pypdfium2]"
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
        import pypdfium2 as pdfium
        import pypdfium2.internal as pdfium_i

        if level == 'block':
            level = 'page'  # Only page is really supported, added block as it is the default for Parxy

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            pdf = pdfium.PdfDocument(stream)

            pages = []
            for page_num, page in enumerate(pdf, start=1):
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                textpage.close()
                page.close()
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
                            text="",
                            blocks=None,
                        )
                    )
            outline = []
            for bm in pdf.get_toc(max_depth=15):
                count, dest = bm.get_count(), bm.get_dest()
                entry = "    " * bm.level
                entry += "[%s] %s -> " % (
                    f"{count:+}" if count != 0 else "*",
                    bm.get_title(),
                )
                if dest:
                    index, (view_mode, view_pos) = dest.get_index(), dest.get_view()
                    entry += "%s  # %s %s" % (
                        index + 1 if index is not None else "?",
                        pdfium_i.ViewmodeToStr.get(view_mode),
                        view_pos,
                    )
                else:
                    entry += "_"
                outline.append(entry)

            span.set_attribute("output.pages", len(pages))

            metadata = pdf.get_metadata_dict()
            pdf.close()

        return Document(
            filename=filename,
            pages=pages,
            outline=outline or None,
            metadata=Metadata(
                title=metadata.get('Title'),
                author=metadata.get('Author'),
                subject=metadata.get('Subject'),
                keywords=metadata.get('Keywords'),
                creator=metadata.get('Creator'),
                producer=metadata.get('Producer'),
                created_at=_parse_pdf_date(metadata.get('CreationDate')),
                updated_at=_parse_pdf_date(metadata.get('ModDate')),
            ),
        )


def _parse_pdf_date(pdf_date: str) -> str | None:
    """
    Parse PDF date string to ISO format.
    PDF date format: D:YYYYMMDDHHmmSSOHH'mm'
    """
    if not pdf_date:
        return None
    try:
        # Remove prefix if present
        if pdf_date.startswith('D:'):
            pdf_date = pdf_date[2:]
        # Only take up to seconds
        dt = datetime.strptime(pdf_date[:14], '%Y%m%d%H%M%S')
        return dt.isoformat()
    except Exception:
        return None

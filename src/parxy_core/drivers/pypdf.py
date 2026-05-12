"""PyPDF driver for parxy."""

import io

from parxy_core.drivers import Driver
from parxy_core.models import Document, Metadata, Page


class PyPDFDriver(Driver):
    """PDF parser using PyPDF for text extraction.

    PyPDF is a pure-python library - lightweight with no binary dependencies.
    Good for simple text extraction, not ideal for complex layouts or tables.
    """

    supported_levels = ["page"]

    def _initialize_driver(self):
        """Initialize PyPDF driver by checking if the library is available."""
        try:
            import pypdf  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "pypdf is required. Install with: pip install parxy[pypdf]"
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
                            text="",
                            blocks=None,
                        )
                    )

            span.set_attribute("output.pages", len(pages))

            outline = _collect_outline(reader.outline, reader) or None

            meta = reader.metadata
            metadata = None
            if meta is not None:
                metadata = Metadata(
                    title=meta.title,
                    author=meta.author,
                    subject=meta.subject,
                    keywords=meta.get('/Keywords'),
                    creator=meta.creator,
                    producer=meta.producer,
                    created_at=_to_iso(meta.creation_date),
                    updated_at=_to_iso(meta.modification_date),
                )

        return Document(
            filename=filename,
            pages=pages,
            outline=outline,
            metadata=metadata,
        )


def _collect_outline(outlines, reader, level: int = 0) -> list[str]:
    entries = []
    for item in outlines:
        if isinstance(item, list):
            entries.extend(_collect_outline(item, reader, level + 1))
        else:
            page_number = reader.get_destination_page_number(item)
            indent = "    " * level
            page = page_number + 1 if page_number is not None else "?"
            entries.append(f"{indent}{item.title} -> {page}")
    return entries


def _to_iso(dt) -> str | None:
    if dt is None:
        return None
    try:
        return dt.replace(tzinfo=None).isoformat()
    except Exception:
        return None

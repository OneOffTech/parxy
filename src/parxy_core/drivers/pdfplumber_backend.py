"""pdfplumber backend driver for parxy."""

import io
from typing import Any

from parxy_core.drivers import Driver
from parxy_core.models import Document, Page


class PDFPlumberBackend(Driver):
    """PDF parser using pdfplumber - excellent for tables.

    pdfplumber uses visual layout analysis to detect and extract tables
    with high accuracy. Good choice for documents with tabular data.
    """

    supported_levels = ["page"]

    def _initialize_driver(self):
        """Initialize pdfplumber driver by checking if the library is available."""
        try:
            import pdfplumber  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "pdfplumber is required. Install with: pip install parxy[pdfplumber]"
            ) from e
        return self

    def _handle(
        self, file: str | io.BytesIO | bytes, level: str = "page", **kwargs
    ) -> Document:
        """Parse PDF to Document object with table extraction.

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
        import pdfplumber

        filename, stream = self.handle_file_input(file)

        with self._trace_parse(filename, stream, **kwargs) as span:
            with pdfplumber.open(io.BytesIO(stream)) as pdf:
                if not pdf.pages:
                    return Document(filename=filename, pages=[])

                pages = []
                for page_num, page in enumerate(pdf.pages):
                    page_content = self._extract_page(page)
                    pages.append(
                        Page(
                            number=page_num,
                            text=page_content.strip() if page_content.strip() else "",
                            blocks=None,
                        )
                    )

                span.set_attribute("output.pages", len(pages))

            return Document(
                filename=filename,
                pages=pages,
            )

    def _extract_page(self, page: Any) -> str:
        """Extract content from a single page."""
        content_parts = []

        # Extract tables
        tables = page.extract_tables()
        if tables:
            for table in tables:
                table_md = self._table_to_markdown(table)
                if table_md:
                    content_parts.append(table_md)

        # Extract text
        text = page.extract_text()
        if text and text.strip():
            content_parts.append(text.strip())

        return "\n\n".join(content_parts)

    def _table_to_markdown(self, table: list[list[str | None]]) -> str:
        """Convert table to GitHub Flavored Markdown."""
        if not table or len(table) < 2:
            return ""

        # Filter empty rows
        table = [row for row in table if any(cell for cell in row if cell)]
        if not table:
            return ""

        max_cols = max(len(row) for row in table)
        if max_cols == 0:
            return ""

        # Normalize rows
        normalized: list[list[str]] = []
        for row in table:
            padded = row + [None] * (max_cols - len(row))
            normalized.append(
                [str(cell).strip() if cell is not None else "" for cell in padded]
            )

        lines = []
        # Header
        lines.append("| " + " | ".join(normalized[0]) + " |")
        # Separator
        lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        # Data rows
        for row in normalized[1:]:  # type: ignore[assignment]
            lines.append("| " + " | ".join(row) + " |")  # type: ignore[arg-type]

        return "\n".join(lines)

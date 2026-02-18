"""Service for rendering documents as content-md."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from parxy_core.models.models import Document


class ContentMdService:
    """Render a :class:`Document` as a content-md string.

    content-md is an open specification for optimised content exchange: a YAML
    frontmatter section followed by CommonMark / GitHub-flavoured Markdown.
    All methods are static; the class acts as a namespace.
    """

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        """Collapse any run of whitespace to a single space and strip."""
        return ' '.join(text.split())

    @staticmethod
    def _yaml_str(value: str) -> str:
        """Wrap *value* in double quotes and escape internal quotes/backslashes."""
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

    @staticmethod
    def _guess_title(document: Document) -> Optional[str]:
        """Infer a title from the first page blocks.

        Prefers an explicit ``doc-title`` role; falls back to the
        highest-ranking (lowest level number) ``heading`` block.
        """
        from parxy_core.models.models import TextBlock

        if not document.pages:
            return None
        first_page = document.pages[0]
        if not first_page.blocks:
            return None

        doc_title = next(
            (
                b
                for b in first_page.blocks
                if isinstance(b, TextBlock) and b.role == 'doc-title' and b.text.strip()
            ),
            None,
        )
        if doc_title:
            return ContentMdService._normalize(doc_title.text)

        headings = [
            b
            for b in first_page.blocks
            if isinstance(b, TextBlock) and b.role == 'heading' and b.text.strip()
        ]
        if not headings:
            return None
        return ContentMdService._normalize(
            min(headings, key=lambda b: b.level or 1).text
        )

    @staticmethod
    def _infer_description(document: Document) -> Optional[str]:
        """Infer a description from document content.

        Uses the ``doc-abstract`` block when present, otherwise the longest
        :class:`TextBlock` across the first two pages.
        """
        from parxy_core.models.models import TextBlock

        blocks = [
            b
            for page in document.pages[:2]
            if page.blocks
            for b in page.blocks
            if isinstance(b, TextBlock) and b.text.strip()
        ]

        abstract = next((b for b in blocks if b.role == 'doc-abstract'), None)
        if abstract:
            return ContentMdService._normalize(abstract.text)

        text_blocks = [b for b in blocks if b.role != 'doc-title']
        if not text_blocks:
            return None
        return ContentMdService._normalize(
            max(text_blocks, key=lambda b: len(b.text)).text
        )

    @staticmethod
    def _build_frontmatter(
        title: str,
        description: Optional[str],
        date: Optional[str],
        license: Optional[str],
        author: Optional[str],
    ) -> str:
        ys = ContentMdService._yaml_str
        lines = ['---', f'title: {ys(title)}']
        if description:
            lines.append(f'description: {ys(description)}')
        if date:
            lines.append(f'date: {ys(date)}')
        if license:
            lines.append(f'license: {ys(license)}')
        if author:
            lines.append(f'author: {ys(author)}')
        lines.append('---')
        return '\n'.join(lines)

    @staticmethod
    def _build_body(document: Document, title: str) -> str:
        from parxy_core.models.models import ImageBlock, TableBlock, TextBlock

        normalize = ContentMdService._normalize
        parts = [f'# {title}']

        for page in document.pages:
            if not page.blocks:
                if page.text.strip():
                    parts.append(normalize(page.text))
                continue

            for block in page.blocks:
                role = (block.role or 'generic').lower()

                if isinstance(block, TextBlock):
                    if role == 'doc-title':
                        # Already the top-level h1 — skip to avoid duplication
                        pass
                    elif role == 'heading':
                        # Shift levels +1: h1 content → h2, per content-md spec
                        shifted = min((block.level or 1) + 1, 6)
                        parts.append(f'{"#" * shifted} {normalize(block.text)}')
                    elif role in ('list', 'listitem'):
                        for line in block.text.splitlines():
                            if line.strip():
                                parts.append(f'- {normalize(line)}')
                    elif role == 'doc-abstract':
                        lang_attr = (
                            f' lang="{document.language}"' if document.language else ''
                        )
                        parts.append(
                            f'<abstract{lang_attr}>\n{normalize(block.text)}\n</abstract>'
                        )
                    else:
                        normalized = normalize(block.text)
                        if normalized:
                            parts.append(normalized)

                elif isinstance(block, ImageBlock):
                    parts.append(f'<figure>\n{block.alt_text or ""}\n</figure>')

                elif isinstance(block, TableBlock):
                    # Preserve table whitespace (column alignment, padding)
                    if block.text.strip():
                        parts.append(block.text.strip())

        return '\n\n'.join(parts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def render(
        document: Document,
        title: Optional[str] = None,
        description: Optional[str] = None,
        date: Optional[str] = None,
        license: Optional[str] = None,
        author: Optional[str] = None,
    ) -> str:
        """Render *document* as a content-md string.

        Parameters
        ----------
        document:
            The document to render.
        title:
            Document title. Falls back to ``metadata.title``, a heading
            inferred from the first page, ``filename``, then ``'Untitled'``.
        description:
            Short summary (~200 characters). Falls back to a ``doc-abstract``
            block, then the longest :class:`TextBlock` in the first two pages.
        date:
            Creation/publication date in ISO 8601. Falls back to
            ``metadata.created_at`` / ``metadata.updated_at``.
        license:
            License name or SPDX identifier.
        author:
            Author name. Falls back to ``metadata.author``.

        Returns
        -------
        str
            The document formatted as content-md.
        """
        resolved_title = (
            title
            or (document.metadata.title if document.metadata else None)
            or ContentMdService._guess_title(document)
            or document.filename
            or 'Untitled'
        )
        resolved_description = description or ContentMdService._infer_description(
            document
        )
        resolved_date = date or (
            (document.metadata.created_at or document.metadata.updated_at)
            if document.metadata
            else None
        )
        resolved_author = author or (
            document.metadata.author if document.metadata else None
        )

        frontmatter = ContentMdService._build_frontmatter(
            title=resolved_title,
            description=resolved_description,
            date=resolved_date,
            license=license,
            author=resolved_author,
        )

        if not document.pages:
            return f'{frontmatter}\n\n# {resolved_title}\n'

        body = ContentMdService._build_body(document, resolved_title)
        return f'{frontmatter}\n\n{body}\n'

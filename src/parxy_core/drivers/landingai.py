import io
from pathlib import Path
from typing import TYPE_CHECKING

from parxy_core.exceptions.authentication_exception import AuthenticationException
from parxy_core.tracing.utils import trace_with_output

# Type hints that will be available at runtime when unstructured is installed
if TYPE_CHECKING:
    from landingai_ade.types import ParseResponse
    from landingai_ade.types.parse_response import ChunkGroundingBox
else:
    # Placeholder types for when package is not installed
    ParseResponse = object
    ChunkGroundingBox = object

from parxy_core.drivers import Driver
from parxy_core.models import Document, Metadata, TextBlock, Page, BoundingBox
from parxy_core.utils import safe_json_dumps

# Mapping from LandingAI ADE chunk types to WAI-ARIA document structure roles
# See docs/explanation/document-roles.md for role definitions
LANDINGAI_TO_ROLE: dict[str, str] = {
    'text': 'paragraph',
    'table': 'table',
    'marginalia': 'generic',  # Mixed content in margins - too generic to map precisely
    'figure': 'figure',
    'logo': 'figure',  # DPT-2 only: logos are visual elements
    'card': 'figure',  # DPT-2 only: ID cards, driver licenses
    'attestation': 'figure',  # DPT-2 only: signatures, stamps, seals
    'scan_code': 'figure',  # DPT-2 only: QR codes, barcodes
    # Footer variants
    'page-footer': 'doc-pagefooter',
    'page_footer': 'doc-pagefooter',
    'footer': 'doc-pagefooter',
    'page-number': 'doc-pagefooter',
    # Footnote variants
    'footnote': 'doc-footnote',
    'note': 'doc-footnote',
    'endnote': 'doc-endnotes',
    'annotation': 'doc-footnote',
    'footer-note': 'doc-footnote',
    # Heading variants
    'heading': 'heading',
    'title': 'doc-title',
    'subtitle': 'doc-subtitle',
    'section': 'heading',
    'chapter': 'doc-chapter',
    # Header variants
    'page-header': 'doc-pageheader',
    'page_header': 'doc-pageheader',
    'page-heading': 'doc-pageheader',
    'header': 'doc-pageheader',
}


class LandingAIADEDriver(Driver):
    def _initialize_driver(self):
        try:
            from landingai_ade import LandingAIADE
        except ImportError as e:
            raise ImportError(
                'LandingAI dependencies not installed. '
                "Install with 'pip install parxy[landingai]'"
            ) from e

        self.__client = LandingAIADE(
            apikey=self._config.api_key.get_secret_value()
            if self._config and self._config.api_key
            else None,
            **self._config.model_dump() if self._config else {},
        )

    def _handle(
        self,
        file: str | io.BytesIO | bytes,
        level: str = 'page',
        **kwargs,
    ) -> Document:
        from landingai_ade import AuthenticationError

        try:
            filename, stream = self.handle_file_input(file)
            with self._trace_parse(filename, stream, **kwargs) as span:
                parse_response = self.__client.parse(document=Path(file), **kwargs)
                span.set_attribute(
                    'output.document', safe_json_dumps(parse_response.model_dump())
                )

        except AuthenticationError as aex:
            raise AuthenticationException(
                message=str(aex),
                service=self.__class__,
            ) from aex

        doc = landingaiade_to_parxy(parse_response)

        # Initialize parsing_metadata if needed
        if doc.parsing_metadata is None:
            doc.parsing_metadata = {}

        # Extract cost information from metadata
        # According to https://docs.landing.ai/ade/ade-json-response.md
        # metadata contains: credit_usage, duration_ms, filename, job_id, page_count, version
        if parse_response.metadata:
            metadata = parse_response.metadata

            # Extract cost estimation from credit_usage
            if hasattr(metadata, 'credit_usage') and metadata.credit_usage is not None:
                doc.parsing_metadata['cost_estimation'] = metadata.credit_usage
                doc.parsing_metadata['cost_estimation_unit'] = 'credits'

            # Extract processing details
            ade_details = {}
            if hasattr(metadata, 'duration_ms') and metadata.duration_ms is not None:
                ade_details['duration_ms'] = metadata.duration_ms
            if hasattr(metadata, 'job_id') and metadata.job_id is not None:
                ade_details['job_id'] = metadata.job_id
            if hasattr(metadata, 'page_count') and metadata.page_count is not None:
                ade_details['page_count'] = metadata.page_count
            if hasattr(metadata, 'version') and metadata.version is not None:
                ade_details['version'] = metadata.version
            if hasattr(metadata, 'filename') and metadata.filename is not None:
                ade_details['filename'] = metadata.filename

            # Add failed_pages if present (for partial content responses)
            if hasattr(metadata, 'failed_pages') and metadata.failed_pages is not None:
                ade_details['failed_pages'] = metadata.failed_pages

            if ade_details:
                doc.parsing_metadata['ade_details'] = ade_details

        return doc


@trace_with_output('converting')
def landingaiade_to_parxy(parsed_data: ParseResponse) -> Document:
    # Group chunks by page
    page_chunks = {}
    for chunk in parsed_data.chunks:
        # Get the first grounding location (chunks can span multiple locations)
        if chunk.grounding:
            page_num = chunk.grounding.page
            if page_num not in page_chunks:
                page_chunks[page_num] = []
            page_chunks[page_num].append(chunk)

    # Determine total page count from metadata
    total_pages = (
        parsed_data.metadata.page_count
        if parsed_data.metadata and parsed_data.metadata.page_count
        else 0
    )

    # Insert empty pages for any gaps in page_chunks
    existing_pages = set(page_chunks.keys())
    for page_num in range(total_pages):
        if page_num not in existing_pages:
            page_chunks[page_num] = []

    # Convert to pages
    pages = []
    for page_num in sorted(page_chunks.keys()):
        chunks = page_chunks[page_num]
        blocks = []
        page_text_parts = []

        for chunk in chunks:
            chunk_text = chunk.markdown

            page_text_parts.append(chunk_text)
            category = chunk.type
            role = LANDINGAI_TO_ROLE.get(category, 'generic') if category else 'generic'

            # Get bounding box from first grounding
            bbox = None
            page = None
            if chunk.grounding:
                grounding = chunk.grounding
                bbox = _convert_bbox(grounding.box)
                page = grounding.page

            # Create the appropriate block type
            block = TextBlock(
                type='text',
                role=role,
                bbox=bbox,
                page=page,
                category=category,
                text=chunk_text,
                source_data=chunk.model_dump(),
            )

            blocks.append(block)

        # Create page
        page_text = '\n'.join(page_text_parts)
        page = Page(
            number=page_num + 1,
            blocks=blocks,
            text=page_text,
            source_data={'page_index': page_num},
        )
        pages.append(page)

    # Create the document
    document = Document(
        filename=parsed_data.metadata.filename,
        pages=pages,
        source_data=parsed_data.metadata.model_dump(),
    )

    return document


def _convert_bbox(box: ChunkGroundingBox) -> BoundingBox:
    """Convert box coordinates from l,t,r,b format to x0,y0,x1,y1 format."""
    return BoundingBox(x0=box.left, y0=box.top, x1=box.right, y1=box.bottom)

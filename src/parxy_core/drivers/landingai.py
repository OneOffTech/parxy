import io
from pathlib import Path
from typing import TYPE_CHECKING

from parxy_core.exceptions.authentication_exception import AuthenticationException

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
            parse_response = self.__client.parse(document=Path(file), **kwargs)

        except AuthenticationError as aex:
            raise AuthenticationException(
                message=str(aex),
                service=self.__class__,
            ) from aex

        return landingaiade_to_parxy(parse_response)


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

    # Convert to pages
    pages = []
    for page_num in sorted(page_chunks.keys()):
        chunks = page_chunks[page_num]
        blocks = []
        page_text_parts = []

        for chunk in chunks:
            chunk_text = chunk.markdown

            page_text_parts.append(chunk_text)
            chunk_type = chunk.type

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
                bbox=bbox,
                page=page,
                category=chunk_type,
                text=chunk_text,
                source_data=chunk.model_dump(),
            )

            blocks.append(block)

        # Create page
        page_text = '\n'.join(page_text_parts)
        page = Page(
            number=page_num,
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

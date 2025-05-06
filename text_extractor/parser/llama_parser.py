from llama_cloud_services import LlamaParse
from llama_cloud_services.parse import ResultType
from parse_document_model import Document, Page
from parse_document_model.attributes import PageAttributes, TextAttributes, BoundingBox
from parse_document_model.document import Text

from text_extractor.parser.pdf_parser import PDFParser


class LlamaParser(PDFParser):

    def __init__(self, api_key: str, server_url: str = "https://api.cloud.llamaindex.ai"):
        self.client = LlamaParse(
            api_key=api_key,
            base_url=server_url,
            result_type=ResultType.TXT
        )

    def parse(self, filename: str, **kwargs) -> Document:
        res = self.client.parse(file_path=filename)
        pages = []
        for i, page in enumerate(res.pages):
            page_nodes = []
            for item in page.items:
                bbox = BoundingBox(min_x=item.bBox.x, min_y=item.bBox.y,
                                   max_x=item.bBox.x + item.bBox.w, max_y=item.bBox.y + item.bBox.h,
                                   page=page.page)
                page_nodes.append(Text(content=item.value if item.value else "",
                                       category=item.type,
                                       attributes=TextAttributes(bounding_box=[bbox], level=item.lvl)))
            pages.append(Page(content=page_nodes, attributes=PageAttributes(page=page.page)))
        return Document(content=pages)

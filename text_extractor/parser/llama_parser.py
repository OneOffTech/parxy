from llama_cloud_services import LlamaParse
from llama_cloud_services.parse import ResultType
from parse_document_model import Document, Page
from parse_document_model.attributes import PageAttributes
from parse_document_model.document import Text

from text_extractor.parser.pdf_parser import PDFParser


class LlamaParser(PDFParser):

    def __init__(self, apy_key: str, server_url: str = "https://api.cloud.llamaindex.ai"):
        self.client = LlamaParse(
            api_key=apy_key,
            base_url=server_url,
            result_type=ResultType.TXT
        )

    def parse(self, filename: str, **kwargs) -> Document:
        res = self.client.load_data(file_path=filename)
        pages = [Page(content=[Text(content=page.text, category="text")],
                      attributes=PageAttributes(page=i + 1)) for i, page in enumerate(res)]
        return Document(content=pages)

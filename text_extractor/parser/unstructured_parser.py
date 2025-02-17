import unstructured_client
from parse_document_model.attributes import PageAttributes
from parse_document_model.document import Text, Page, Document
from unstructured_client.models import shared

from text_extractor.parser.pdf_parser import PDFParser


class UnstructuredParser(PDFParser):

    def __init__(self, apy_key: str, server_url: str):
        self.client = unstructured_client.UnstructuredClient(
            api_key_auth=apy_key,
            server_url=server_url,
        )

    def parse(self, filename: str, **kwargs) -> Document:
        req = {
            "partition_parameters": {
                "files": {
                    "content": open(filename, "rb"),
                    "file_name": filename,
                },
                "strategy": shared.Strategy.HI_RES,
                "languages": ['eng'],
                "split_pdf_allow_failed": True,
                "split_pdf_concurrency_level": 15
            }
        }
        res = self.client.general.partition(request=req)
        element_dicts = [element for element in res.elements]
        element_nodes = [Text(content=element["text"], category=element["type"]) for element in res.elements]
        pages = [Page(content=[], attributes=PageAttributes(page=i))
                 for i in range(element_dicts[-1]["metadata"]["page_number"])]
        for el_dict, el_node in zip(element_dicts, element_nodes):
            pages[el_dict["metadata"]["page_number"] - 1].content.append(el_node)
        return Document(content=pages)

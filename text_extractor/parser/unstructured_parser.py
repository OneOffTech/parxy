import unstructured_client
from parse_document_model.attributes import PageAttributes, BoundingBox, TextAttributes
from parse_document_model.document import Text, Page, Document
from unstructured_client.models import shared

from text_extractor.parser.pdf_parser import PDFParser


class UnstructuredParser(PDFParser):

    def __init__(self, api_key: str, server_url: str):
        self.client = unstructured_client.UnstructuredClient(
            api_key_auth=api_key,
            server_url=server_url,
        )

    def parse(self, filename: str, **kwargs) -> Document:
        with open(filename, "rb") as f:
            req = {
                "partition_parameters": {
                    "files": {
                        "content": f,
                        "file_name": filename,
                    },
                    "strategy": shared.Strategy.HI_RES,
                    "languages": ['eng'],
                    "split_pdf_allow_failed": True,
                    "split_pdf_concurrency_level": 15,
                    "coordinates": True
                }
            }
            res = self.client.general.partition(request=req)
        element_dicts = [element for element in res.elements]
        element_nodes = []
        for element in res.elements:
            metadata = element["metadata"]
            coordinates = metadata["coordinates"]
            points = coordinates["points"]
            if points:
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                bbox = BoundingBox(
                    min_x=min(xs),
                    min_y=min(ys),
                    max_x=max(xs),
                    max_y=max(ys),
                    page=metadata["page_number"]
                )
                bboxes = [bbox]
            else:
                bboxes = []
            text = Text(content=element["text"],
                        category=element["type"],
                        attributes=TextAttributes(bounding_box=bboxes),
                        )
            element_nodes.append(text)
        if len(element_nodes) == 0:
            return Document(content=[])
        pages = [Page(content=[], attributes=PageAttributes(page=i))
                 for i in range(element_dicts[-1]["metadata"]["page_number"])]
        for el_dict, el_node in zip(element_dicts, element_nodes):
            pages[el_dict["metadata"]["page_number"] - 1].content.append(el_node)
        return Document(content=pages)

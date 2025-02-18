from typing import Optional, List

from text_extractor.parser.llama_parser import LlamaParser
from text_extractor.parser.pdfact_parser import PdfactParser
from text_extractor.parser.pymupdf_parser import PymupdfParser
from text_extractor.parser.unstructured_parser import UnstructuredParser


def parse_with_llama(file_url: str, service_url: str, api_key: str):
    try:
        parser = LlamaParser(api_key=api_key, server_url=service_url)
        document = parser.parse(filename=file_url)
    except Exception as e:
        raise e
    return document


def parse_with_pdfact(file_url: str, service_url, roles: Optional[List[str]] = None):
    try:
        parser = PdfactParser(service_url)
        document = parser.parse(filename=file_url, roles=roles)
    except Exception as e:
        raise e
    return document


def parse_with_pymupdf(file_url: str):
    try:
        parser = PymupdfParser()
        document = parser.parse(filename=file_url)
    except Exception as e:
        raise e
    return document


def parse_with_unstructured(file_url: str, service_url: str, api_key: str):
    try:
        parser = UnstructuredParser(api_key=api_key, server_url=service_url)
        document = parser.parse(filename=file_url)
    except Exception as e:
        raise e
    return document

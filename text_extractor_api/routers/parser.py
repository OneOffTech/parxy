import hashlib
import logging
import os
from typing import List, Optional

import requests
from fastapi import APIRouter, HTTPException
from parse_document_model import Document
from requests.exceptions import HTTPError, RequestException

from text_extractor import assistant
from text_extractor_api.config import settings
from text_extractor_api.models import ExtractTextRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/extract-text", response_model=Document)
def extract_text(request: ExtractTextRequest) -> Document:
    logger.info("Received parse request.")

    # Check the document format
    if request.mime_type != 'application/pdf':
        mime = request.mime_type
        raise HTTPException(status_code=422, detail=f"Unsupported mime type '{mime}'. Expecting application/pdf.")

    # Check the driver
    if request.driver.lower() not in ["llama", "pdfact", "pymupdf", "unstructured"]:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported driver. Expecting one of 'llama', 'pdfact', 'pymupdf' or "
                                   f"'unstructured'. Received [{request.driver}].")

    # Check the validity of the url
    try:
        resp = requests.head(request.url, allow_redirects=True, timeout=30)
    except (HTTPError, RequestException) as http_err:
        logger.exception("Error while checking URL status.", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error while checking URL status [{http_err}]")
    if resp.status_code in [401, 403]:
        logger.warning(f"Authentication required for URL: {request.url}")
        raise HTTPException(
            status_code=422,
            detail=f"The provided file URL [{request.url}] requires authentication. "
                   "Authentication protected URLs are currently not supported."
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"Error while checking URL status. {resp.content}")

    # Download the file and store it in a temp dir
    # pymupdf can read directly from an url
    file_url = request.url
    if request.driver.lower() in ["llama", "pdfact", "unstructured"]:
        os.makedirs("tmp", exist_ok=True)
        filename = hashlib.sha256(file_url.encode()).hexdigest() + ".pdf"
        tmp_filepath = os.path.join("tmp", filename)
        try:
            resp = requests.get(file_url, allow_redirects=True, timeout=120)
            resp.raise_for_status()
            with open(tmp_filepath, 'wb') as f:
                f.write(resp.content)
            file_url = tmp_filepath
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Unable to download the file at the specified URL. {str(e)}")

    # Parse the file
    try:
        document = parse(file_url, request.driver.lower(), request.roles)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while parsing file. {str(e)}")
    finally:
        if os.path.exists(file_url):
            os.remove(file_url)
    return document


def parse(file_url: str, driver: str, roles: Optional[List[str]] = None) -> Document:
    kwargs = {"file_url": file_url}
    if driver == "pdfact":
        kwargs["service_url"] = settings.pdfact_url
        kwargs["roles"] = roles
    elif driver == "llama":
        kwargs["service_url"] = settings.llama_url
        kwargs["api_key"] = settings.llama_api_key
    elif driver == "unstructured":
        kwargs["service_url"] = settings.unstructured_url
        kwargs["api_key"] = settings.unstructured_api_key
    return getattr(assistant, f"parse_with_{driver}")(**kwargs)

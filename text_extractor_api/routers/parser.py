import hashlib
import logging
import os

import requests
from fastapi import APIRouter, HTTPException
from requests.exceptions import HTTPError, Timeout, RequestException

from parse_document_model import Document
from text_extractor.parser.pdfact_parser import PdfactParser
from text_extractor.parser.pymupdf_parser import PymupdfParser
from text_extractor_api.config import settings
from text_extractor_api.models import ExtractTextRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/extract-text", response_model=Document)
async def parse_pdf(request: ExtractTextRequest) -> Document:
    logger.info("Received parse request.")
    resource_path: str = os.environ.get("RESOURCE_PATH", "/tmp")

    if request.mime_type != 'application/pdf':
        mime = request.mime_type
        raise HTTPException(status_code=422, detail=f"Unsupported mime type[{mime}]. Expecting application/pdf.")

    if request.driver.lower() not in ["pdfact", "pymupdf"]:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported driver. Expecting 'pdfact' or 'pymupdf', received [{request.driver}].")

    try:
        os.mkdir(resource_path)
    except FileExistsError:
        pass

    if request.mime_type != 'application/pdf':
        mime = request.mime_type
        logger.warning(f"Unsupported format [{mime}]")
        raise HTTPException(status_code=422,
                            detail=f"Unsupported mime type. Expecting application/pdf received [{mime}].")

    filename = hashlib.sha256(request.url.encode()).hexdigest()
    extension = request.mime_type.split("/")[-1]
    filename = f"{filename}.{extension}"
    logger.info(f"Parsing {filename}")
    file_path = os.path.join(resource_path, filename)

    try:
        head_resp = requests.head(request.url, allow_redirects=True, timeout=30)

        if head_resp.status_code in [401, 403]:
            logger.warning(f"Authentication required for URL: {request.url}")
            raise HTTPException(
                status_code=422,
                detail=f"The provided file URL [{request.url}] requires authentication. "
                       "Authentication protected URLs are currently not supported."
            )

        head_resp.raise_for_status()
    except (HTTPError, RequestException) as http_err:
        logger.exception("Error while checking URL status.", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error while checking URL status [{http_err}]")

    document = None
    if request.driver.lower() == "pdfact":
        try:
            logger.info(f"Forwarding request to PDFAct for {request.url}")
            parser = PdfactParser(settings.pdfact_url)
            document = parser.parse(filename=request.url, roles=request.roles)
        except RequestException as e:
            if isinstance(e, HTTPError):
                logger.exception(f"PDFAct returned an error for {request.url}", exc_info=True)
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Unexpected error while processing [{request.url}]: {e}"
                )
            logger.exception(f"Error while connecting to PDFAct or parsing file. {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error while processing [{request.url}]")
        except Exception as err:
            logger.exception(f"Error while parsing file. {str(err)}", exc_info=True)
            raise HTTPException(status_code=400, detail="Error while parsing file")

    elif request.driver.lower() == "pymupdf":
        try:
            resp = requests.get(request.url, allow_redirects=True, timeout=120)
            resp.raise_for_status()
            with open(file_path, 'wb') as f:
                f.write(resp.content)
            logger.info(f"Parsing {filename} with PyMuPDF")
            parser = PymupdfParser()
            document = parser.parse(filename=file_path)
        except HTTPError as http_err:
            logger.exception("Error while downloading file.", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Error while downloading file [{http_err}]")
        except Timeout as http_timeout:
            logger.exception("Timeout while downloading file.", exc_info=True)
            raise HTTPException(status_code=408, detail=f"File download not completed [{http_timeout}]")
        except Exception as err:
            logger.exception(f"Error while parsing file with pymupdf. {str(err)}", exc_info=True)
            raise HTTPException(status_code=400, detail="Error while parsing file")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    return document


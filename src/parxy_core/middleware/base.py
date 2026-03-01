"""Middleware base classes for Parxy document processing.

This module defines the abstract middleware interface that allows preprocessing
and postprocessing of documents through the parsing pipeline.
"""

from abc import ABC
from typing import Callable

from parxy_core.models import Document, ParsingRequest


class Middleware(ABC):
    """Abstract base class for document processing middleware.

    Middleware allows you to hook into the document parsing pipeline at two points:
    - `handle()`: Called BEFORE parsing, receives a ParsingRequest
    - `terminate()`: Called AFTER parsing, receives the parsed Document

    Middleware are executed in chains:
    - handle() chain: First middleware's handle() -> next -> ... -> driver
    - terminate() chain: driver -> ... -> last middleware's terminate()
    """

    def handle(
        self,
        request: ParsingRequest,
        next: Callable[[ParsingRequest], Document],
    ) -> Document:
        """Process the request before parsing."""
        return next(request)

    def terminate(
        self,
        document: Document,
        next: Callable[[Document], Document],
    ) -> Document:
        """Process the document after parsing."""
        return next(document)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'


class SimpleMiddleware(Middleware):
    """Simplified middleware base for handle-only or terminate-only implementations."""

    def handle(
        self,
        request: ParsingRequest,
        next: Callable[[ParsingRequest], Document],
    ) -> Document:
        """Default implementation that passes through to next."""
        return next(request)

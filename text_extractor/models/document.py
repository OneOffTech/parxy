from abc import ABC
from typing import List, Optional, Any

from pydantic import BaseModel


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Style(BaseModel):
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    font_style: Optional[str] = None
    color: Optional[str] = None
    alpha: Optional[int] = None
    weight: Optional[float] = None


class Character(BaseModel):
    text: str
    bbox: Optional[BoundingBox] = None
    style: Optional[Style] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None


class Span(BaseModel):
    text: str
    bbox: Optional[BoundingBox] = None
    style: Optional[Style] = None
    characters: Optional[List[Character]] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None


class Line(BaseModel):
    text: str
    bbox: Optional[BoundingBox] = None
    spans: Optional[List[Span]] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None


class Block(BaseModel, ABC):
    type: str
    bbox: Optional[BoundingBox] = None
    page: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None


class TextBlock(Block):
    category: Optional[str] = None
    level: Optional[int] = None
    lines: Optional[List[Line]] = None
    text: str


class ImageBlock(Block):
    ...


class TableBlock(Block):
    ...


class Page(BaseModel):
    number: int
    width: Optional[float] = None
    height: Optional[float] = None
    blocks: Optional[List[Block]] = None
    text: str
    source_data: Optional[dict[str, Any]] = None


class Metadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    mod_date: Optional[str] = None


class Document(BaseModel):
    filename: Optional[str] = None
    language: Optional[str] = None
    metadata: Optional[Metadata] = None
    pages: List[Page]
    outline: Optional[List[str]] = None
    source_data: Optional[dict[str, Any]] = None

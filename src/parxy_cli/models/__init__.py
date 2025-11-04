from enum import Enum
from typing import Annotated
# from typer import Context, Option


class Level(str, Enum):
    """Valid extraction levels."""

    PAGE = 'page'
    BLOCK = 'block'
    LINE = 'line'
    SPAN = 'span'
    CHARACTER = 'character'


class OutputMode(str, Enum):
    """Valid output modes for parse command."""

    JSON = 'json'
    PLAIN = 'plain'
    MARKDOWN = 'markdown'

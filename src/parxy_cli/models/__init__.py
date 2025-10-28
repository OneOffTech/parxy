from enum import Enum


class Level(str, Enum):
    """Valid extraction levels."""

    PAGE = 'page'
    BLOCK = 'block'
    LINE = 'line'
    SPAN = 'span'
    CHARACTER = 'character'

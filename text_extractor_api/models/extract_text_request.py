from typing import List, Optional

from pydantic import BaseModel


class ExtractTextRequest(BaseModel):
    url: str
    driver: str
    roles: Optional[List[str]] = None

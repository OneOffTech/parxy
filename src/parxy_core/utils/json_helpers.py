"""JSON serialization helpers for handling binary content."""

import base64
import json
from typing import Any


class BytesJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles bytes by encoding to base64.

    This encoder converts bytes objects to base64-encoded strings prefixed
    with 'base64:' to indicate the encoding format. This allows binary data
    like images to be safely serialized to JSON.

    Example
    -------
    >>> data = {'image': b'\\x89PNG...', 'text': 'hello'}
    >>> json.dumps(data, cls=BytesJSONEncoder)
    '{"image": "base64:iVBORw0KG...", "text": "hello"}'
    """

    def default(self, obj: Any) -> Any:
        """Convert bytes to base64-encoded string.

        Parameters
        ----------
        obj : Any
            Object to encode.

        Returns
        -------
        Any
            Encoded object. Bytes are converted to base64 strings,
            other types are handled by the parent encoder.
        """
        if isinstance(obj, bytes):
            return f'base64:{base64.b64encode(obj).decode("ascii")}'
        return super().default(obj)


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize object to JSON string, handling bytes objects.

    This is a convenience wrapper around json.dumps that uses BytesJSONEncoder
    to handle binary data. Any bytes objects in the data structure will be
    automatically converted to base64-encoded strings.

    Parameters
    ----------
    obj : Any
        Object to serialize to JSON.
    **kwargs
        Additional arguments passed to json.dumps (e.g., indent, sort_keys).

    Returns
    -------
    str
        JSON string representation of the object.

    Example
    -------
    >>> data = {'image': b'\\x89PNG...', 'text': 'hello'}
    >>> safe_json_dumps(data, indent=2)
    '{\\n  "image": "base64:iVBORw0KG...",\\n  "text": "hello"\\n}'
    """
    return json.dumps(obj, cls=BytesJSONEncoder, **kwargs)

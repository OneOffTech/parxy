import io
import json
import os
from datetime import datetime
from typing import Any


class Tracer:
    """Tracing service to store debug traces from document processing services."""

    def __init__(self, enabled=False, path='storage/traces'):
        """Initialize the tracing service."""
        self._enabled = enabled
        self._directory = path

    def _get_storage_directory(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self._directory,
        )

    def trace(
        self,
        driver: str,
        content: Any,
        file_source: str | io.BytesIO | bytes,
    ) -> None:
        """Save processing trace for debugging purposes.

        Parameters
        ----------
        content : Any
            The content to save (document or response from processing service)
        file_source : str | io.BytesIO | bytes
            The original input file/source
        """

        if not self._enabled:
            return

        # Create dumps directory if not specified
        trace_dir = self._get_storage_directory()

        os.makedirs(trace_dir, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if isinstance(file_source, str):
            source_name = os.path.splitext(os.path.basename(file_source))[0]
        elif isinstance(file_source, io.BytesIO) and hasattr(file_source, 'name'):
            source_name = os.path.splitext(os.path.basename(file_source.name))[0]
        else:
            source_name = 'unnamed_source'

        filename = f'{source_name}_{timestamp}.json'
        filepath = os.path.join(trace_dir, filename)

        # Prepare trace data
        trace_data = {
            'timestamp': timestamp,
            'driver': driver,
            'source': str(file_source),
            'config': self._config,
        }

        if hasattr(content, 'model_dump'):
            trace_data['output'] = content.model_dump()
        else:
            trace_data['output'] = str(content)
        # else:
        #     trace_data["error"] = {
        #         "type": error.__class__.__name__ if error else "Unknown",
        #         "message": str(error) if error else str(content),
        #     }

        # Save trace file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, indent=2, ensure_ascii=False)

        self._logger.debug(f'Trace saved to {filepath}')

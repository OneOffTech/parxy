#!/bin/sh
uvicorn "text_extractor_api.main:app" --host 0.0.0.0 --port 5000 --loop asyncio

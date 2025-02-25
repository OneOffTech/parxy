import logging
import os
import sys
from datetime import datetime

from fastapi import FastAPI

from text_extractor_api.routers import parser

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)
# Define log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# Create log handlers
stream_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler(f"logs/log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
# Set formatter
formatter = logging.Formatter(LOG_FORMAT)
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
# Configure the root logger (applies to FastAPI and Uvicorn)
logging.basicConfig(
    level=logging.INFO,
    handlers=[stream_handler, file_handler],
    format=LOG_FORMAT,
)
# Get logger instance
logger = logging.getLogger("text-extractor")
logger.setLevel(logging.DEBUG)
logger.info("Logger initialized.")
# Configure Uvicorn's loggers to use the same settings without duplication
for uvicorn_logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
    uvicorn_logger = logging.getLogger(uvicorn_logger_name)
    uvicorn_logger.handlers.clear()  # Remove default handlers
    uvicorn_logger.propagate = False  # Prevent log duplication
    uvicorn_logger.setLevel(logging.DEBUG)
    uvicorn_logger.addHandler(stream_handler)
    uvicorn_logger.addHandler(file_handler)

# Initialize FastAPI app
app = FastAPI()
app.include_router(parser.router)


async def root():
    logger.info("Welcome to text extractor!")
    return {"message": "Welcome to text extractor!"}

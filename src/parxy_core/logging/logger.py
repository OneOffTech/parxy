import logging
import sys
from datetime import datetime

def create_isolated_logger(name: str, level: int = logging.ERROR, 
                          log_format: str = None, 
                          propagate: bool = False,
                          add_console_handler: bool = True,
                          add_file_handler: bool = False,
                          file_path: str = None) -> logging.Logger:
    """
    Create an isolated logger that doesn't interfere with other loggers.
    
    Args:
        name: Logger name (should be unique to your application)
        level: Logging level (default: logging.ERROR)
        log_format: Custom log format string
        propagate: Whether to propagate to parent loggers (default: False)
        add_console_handler: Add console output handler (default: True)
        add_file_handler: Add file output handler (default: False)
        file_path: Path for log file (required if add_file_handler=True)
    
    Returns:
        Configured logger instance
    """
    
    # Create logger with unique name
    logger = logging.getLogger(name)
    
    # Prevent interference with other loggers
    logger.propagate = propagate
    
    # Set logging level
    logger.setLevel(level)
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Default format if none provided
    if log_format is None:
        log_format = '[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(log_format)
    
    # Add handlers

    if not add_console_handler and not add_file_handler:
        null_handler = logging.NullHandler()
        null_handler.setLevel(level)
        null_handler.setFormatter(formatter)
        logger.addHandler(null_handler)

    if add_console_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if add_file_handler:
        if file_path is None:
            file_path = f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def create_null_logger(name: str, level: int = logging.ERROR) -> logging.Logger:
    """
    Create a logger that do not store or output any log messages.
    
    Args:
        name: Logger name (should be unique to your application)
        level: Logging level (default: logging.ERROR)
    
    Returns:
        Configured logger instance
    """
    
    return create_isolated_logger(name=name, level=level, add_console_handler=False, add_file_handler=False)
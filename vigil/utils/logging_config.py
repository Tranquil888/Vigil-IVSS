"""
Logging configuration for Vigil surveillance system.
"""

import logging
import os
from typing import Optional
from vigil.config.constants import LOG_FILE, LOG_FORMAT


class VigilLogger:
    """Centralized logging management for Vigil system."""
    
    def __init__(self):
        self.loggers = {}
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup basic logging configuration."""
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            handlers=[
                logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the specified name."""
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]
    
    def log_exception(self, logger: logging.Logger, error: Exception, context: str = "") -> None:
        """Log an exception with context information."""
        error_msg = f"[{context}] {type(error).__name__}: {error}"
        logger.error(error_msg, exc_info=True)


# Global logger instance
vigil_logger = VigilLogger()

# Convenience functions for getting specific loggers
def get_main_logger() -> logging.Logger:
    """Get the main application logger."""
    return vigil_logger.get_logger("vigil.main")

def get_auth_logger() -> logging.Logger:
    """Get the authentication logger."""
    return vigil_logger.get_logger("vigil.auth")

def get_camera_logger() -> logging.Logger:
    """Get the camera logger."""
    return vigil_logger.get_logger("vigil.camera")

def get_recognition_logger() -> logging.Logger:
    """Get the recognition logger."""
    return vigil_logger.get_logger("vigil.recognition")

def get_database_logger() -> logging.Logger:
    """Get the database logger."""
    return vigil_logger.get_logger("vigil.database")

def get_ui_logger() -> logging.Logger:
    """Get the UI logger."""
    return vigil_logger.get_logger("vigil.ui")

def get_stream_logger() -> logging.Logger:
    """Get the streaming logger."""
    return vigil_logger.get_logger("vigil.stream")

def get_events_logger() -> logging.Logger:
    """Get the events logger."""
    return vigil_logger.get_logger("vigil.events")

def get_video_logger() -> logging.Logger:
    """Get the video processing logger."""
    return vigil_logger.get_logger("vigil.video")


# Export the main logging function
def log_exception(logger: logging.Logger, error: Exception, context: str = "") -> None:
    """Log an exception with context information."""
    vigil_logger.log_exception(logger, error, context)


def safe_execute(func, logger: logging.Logger, context: str = "", default=None):
    """Safely execute a function with error handling."""
    try:
        return func()
    except Exception as e:
        log_exception(logger, e, context)
        return default

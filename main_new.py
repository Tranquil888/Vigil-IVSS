"""
Vigil - Intelligent Video Surveillance System
Entry point for the modular application.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vigil.core.app import app
from vigil.utils.logging_config import get_main_logger


def main():
    """Main entry point for the Vigil application."""
    logger = get_main_logger()
    
    try:
        logger.info("Starting Vigil surveillance system")
        
        # Initialize the application
        if not app.initialize():
            logger.error("Failed to initialize application")
            return 1
        
        # Start the application
        app.start()
        
        return 0
        
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        return 1
    finally:
        logger.info("Vigil application shutdown complete")


if __name__ == "__main__":
    sys.exit(main())

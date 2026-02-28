"""
Application constants for Vigil surveillance system.
"""

import os

# Database file paths
SETTING_DB_PATH = "data/setting.db"
AUTH_DB_PATH = "data/authentication.db"
OBJECTS_DB_PATH = "data/objects.db"
CAMERA_DB_PATH = "data/camerasetting.db"
EVENTS_DB_PATH = "data/events.db"

# Default settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "8000"
DEFAULT_RESOLUTION = "704"
DEFAULT_QUALITY = "90"
DEFAULT_FPS = 20

# User roles
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"

# Recognition algorithms
ALGORITHM_CNN = "cnn"
ALGORITHM_HOG = "hog"

# Object types for filtering
OBJECT_TYPES = ["Person", "Unknown", "Vehicle", "Animal", "Other"]

# Video codecs
CODEC_XVID = "XVID"
CODEC_MP4V = "MP4V"

# File extensions
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']

# Model files
ENCODINGS_FILE = "encodings.pickle"
DATASET_DIR = "data/dataset"

# UI Constants
WINDOW_TITLE = "Vigil - Intelligent Video Surveillance System"
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600

# Logging
LOG_FILE = "log.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"

# Security
MAX_LOGIN_ATTEMPTS = 3
SESSION_TIMEOUT = 3600  # 1 hour


def get_data_dir() -> str:
    """Get the data directory path."""
    return "data"

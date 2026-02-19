"""
Custom exception classes for Vigil surveillance system.
"""


class VigilException(Exception):
    """Base exception class for Vigil system."""
    pass


class DatabaseError(VigilException):
    """Exception raised for database-related errors."""
    pass


class CameraError(VigilException):
    """Exception raised for camera-related errors."""
    pass


class AuthenticationError(VigilException):
    """Exception raised for authentication failures."""
    pass


class AuthorizationError(VigilException):
    """Exception raised for authorization failures."""
    pass


class RecognitionError(VigilException):
    """Exception raised for face/object recognition errors."""
    pass


class StreamError(VigilException):
    """Exception raised for video streaming errors."""
    pass


class ConfigurationError(VigilException):
    """Exception raised for configuration-related errors."""
    pass


class ModelError(VigilException):
    """Exception raised for model training/loading errors."""
    pass


class TrainingError(VigilException):
    """Exception raised for face recognition training errors."""
    pass


class VideoProcessingError(VigilException):
    """Exception raised for video processing errors."""
    pass


class FileOperationError(VigilException):
    """Exception raised for file operation errors."""
    pass


class ValidationError(VigilException):
    """Exception raised for data validation errors."""
    pass


class SystemResourceError(VigilException):
    """Exception raised for system resource issues."""
    pass

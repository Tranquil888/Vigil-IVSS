"""
Video processing module for Vigil surveillance system.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from vigil.core.exceptions import VideoProcessingError, RecognitionError
from vigil.utils.logging_config import get_video_logger
from vigil.config.settings import settings


class FrameProcessor:
    """Processes video frames for recognition and analysis."""
    
    def __init__(self):
        self.logger = get_video_logger()
        self.target_resolution = None
        self.jpeg_quality = 90
        self._load_processing_settings()
    
    def _load_processing_settings(self) -> None:
        """Load processing settings from configuration."""
        try:
            # Get streaming resolution and quality
            resolution = settings.get_setting('stream_res_qua', '704')
            quality = settings.get_setting('stream_res_qua', '90')  # Second value is quality
            
            self.target_resolution = int(resolution)
            self.jpeg_quality = int(quality) if quality else 90
            
            self.logger.info(f"Processing settings loaded: resolution={self.target_resolution}, quality={self.jpeg_quality}")
            
        except Exception as e:
            self.logger.error(f"Error loading processing settings: {e}")
            self.target_resolution = 704
            self.jpeg_quality = 90
    
    def resize_frame(self, frame: np.ndarray, target_width: Optional[int] = None) -> np.ndarray:
        """
        Resize frame to target width while maintaining aspect ratio.
        
        Args:
            frame: Input frame
            target_width: Target width (uses default if None)
            
        Returns:
            Resized frame
        """
        if target_width is None:
            target_width = self.target_resolution
        
        if target_width is None:
            return frame
        
        try:
            height, width = frame.shape[:2]
            aspect_ratio = width / height
            
            if aspect_ratio == 0:
                raise VideoProcessingError("Invalid frame dimensions")
            
            target_height = int(target_width / aspect_ratio)
            
            resized = cv2.resize(frame, (target_width, target_height))
            return resized
            
        except Exception as e:
            self.logger.error(f"Error resizing frame: {e}")
            raise VideoProcessingError(f"Failed to resize frame: {e}")
    
    def encode_frame(self, frame: np.ndarray, quality: Optional[int] = None) -> bytes:
        """
        Encode frame to JPEG bytes.
        
        Args:
            frame: Input frame
            quality: JPEG quality (uses default if None)
            
        Returns:
            Encoded frame as bytes
        """
        if quality is None:
            quality = self.jpeg_quality
        
        try:
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            if not success:
                raise VideoProcessingError("Failed to encode frame to JPEG")
            
            return buffer.tobytes()
            
        except Exception as e:
            self.logger.error(f"Error encoding frame: {e}")
            raise VideoProcessingError(f"Failed to encode frame: {e}")
    
    def process_frame_for_streaming(self, frame: np.ndarray) -> bytes:
        """
        Process frame for web streaming (resize + encode).
        
        Args:
            frame: Input frame
            
        Returns:
            Processed frame as JPEG bytes
        """
        try:
            # Resize frame
            resized_frame = self.resize_frame(frame)
            
            # Encode to JPEG
            encoded_frame = self.encode_frame(resized_frame)
            
            return encoded_frame
            
        except Exception as e:
            self.logger.error(f"Error processing frame for streaming: {e}")
            raise VideoProcessingError(f"Failed to process frame for streaming: {e}")
    
    def convert_color_space(self, frame: np.ndarray, conversion: int = cv2.COLOR_BGR2RGB) -> np.ndarray:
        """
        Convert frame color space.
        
        Args:
            frame: Input frame
            conversion: OpenCV color conversion constant
            
        Returns:
            Converted frame
        """
        try:
            return cv2.cvtColor(frame, conversion)
        except Exception as e:
            self.logger.error(f"Error converting color space: {e}")
            raise VideoProcessingError(f"Failed to convert color space: {e}")
    
    def apply_gaussian_blur(self, frame: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """
        Apply Gaussian blur to frame.
        
        Args:
            frame: Input frame
            kernel_size: Blur kernel size (must be odd)
            
        Returns:
            Blurred frame
        """
        try:
            if kernel_size % 2 == 0:
                kernel_size += 1  # Ensure odd number
            
            return cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)
            
        except Exception as e:
            self.logger.error(f"Error applying Gaussian blur: {e}")
            raise VideoProcessingError(f"Failed to apply Gaussian blur: {e}")
    
    def detect_motion(self, frame1: np.ndarray, frame2: np.ndarray, threshold: int = 25) -> List[Tuple[int, int, int, int]]:
        """
        Detect motion between two frames.
        
        Args:
            frame1: First frame
            frame2: Second frame
            threshold: Motion detection threshold
            
        Returns:
            List of bounding boxes for motion areas
        """
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            
            # Calculate difference
            diff = cv2.absdiff(gray1, gray2)
            
            # Apply threshold
            _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Get bounding boxes
            motion_areas = []
            for contour in contours:
                if cv2.contourArea(contour) > 500:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    motion_areas.append((x, y, w, h))
            
            return motion_areas
            
        except Exception as e:
            self.logger.error(f"Error detecting motion: {e}")
            raise VideoProcessingError(f"Failed to detect motion: {e}")
    
    def draw_rectangle(self, frame: np.ndarray, rect: Tuple[int, int, int, int], 
                      color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> np.ndarray:
        """
        Draw rectangle on frame.
        
        Args:
            frame: Input frame
            rect: Rectangle (x, y, width, height)
            color: Rectangle color (B, G, R)
            thickness: Line thickness
            
        Returns:
            Frame with rectangle drawn
        """
        try:
            x, y, w, h = rect
            result_frame = frame.copy()
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), color, thickness)
            return result_frame
        except Exception as e:
            self.logger.error(f"Error drawing rectangle: {e}")
            return frame
    
    def draw_text(self, frame: np.ndarray, text: str, position: Tuple[int, int],
                  color: Tuple[int, int, int] = (0, 255, 0), scale: float = 1.0,
                  thickness: int = 2) -> np.ndarray:
        """
        Draw text on frame.
        
        Args:
            frame: Input frame
            text: Text to draw
            position: Text position (x, y)
            color: Text color (B, G, R)
            scale: Text scale
            thickness: Text thickness
            
        Returns:
            Frame with text drawn
        """
        try:
            result_frame = frame.copy()
            cv2.putText(result_frame, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                       scale, color, thickness)
            return result_frame
        except Exception as e:
            self.logger.error(f"Error drawing text: {e}")
            return frame
    
    def get_frame_info(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Get information about a frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Dictionary with frame information
        """
        try:
            height, width = frame.shape[:2]
            channels = frame.shape[2] if len(frame.shape) > 2 else 1
            
            return {
                'width': width,
                'height': height,
                'channels': channels,
                'dtype': frame.dtype,
                'size': frame.size,
                'aspect_ratio': width / height if height > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting frame info: {e}")
            return {}
    
    def validate_frame(self, frame: np.ndarray) -> bool:
        """
        Validate frame format and dimensions.
        
        Args:
            frame: Input frame
            
        Returns:
            True if frame is valid, False otherwise
        """
        try:
            if frame is None:
                return False
            
            if not isinstance(frame, np.ndarray):
                return False
            
            if len(frame.shape) < 2:
                return False
            
            if frame.shape[0] == 0 or frame.shape[1] == 0:
                return False
            
            return True
            
        except Exception:
            return False


# Global frame processor instance
frame_processor = FrameProcessor()

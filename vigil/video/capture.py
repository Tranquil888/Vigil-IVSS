"""
Video capture module for Vigil surveillance system.
"""

import cv2
import time
import threading
from typing import Optional, Callable, Tuple
from vigil.core.exceptions import CameraError, VideoProcessingError
from vigil.utils.logging_config import get_video_logger
from vigil.config.settings import settings


class VideoCapture:
    """Manages video capture from cameras and files."""
    
    def __init__(self):
        self.logger = get_video_logger()
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.current_source = None
        self.frame_callback: Optional[Callable] = None
        self.capture_thread: Optional[threading.Thread] = None
        self.fps = 0
        self.width = 0
        self.height = 0
        self.frame_count = 0
        
        # Load camera settings
        self._load_camera_settings()
    
    def _load_camera_settings(self) -> None:
        """Load camera configuration from settings."""
        try:
            # Get default camera settings
            self.default_camera = "channel_01"
            camera_info = self._get_camera_info(self.default_camera)
            
            if camera_info:
                self.camera_link = camera_info.get('link')
                self.camera_mode = camera_info.get('cam_set_a', '0')
                self.logger.info(f"Camera settings loaded: link={self.camera_link}, mode={self.camera_mode}")
            else:
                self.camera_link = None
                self.camera_mode = '0'
                self.logger.warning("No camera settings found, using defaults")
                
        except Exception as e:
            self.logger.error(f"Error loading camera settings: {e}")
            self.camera_link = None
            self.camera_mode = '0'
    
    def _get_camera_info(self, camera_id: str) -> Optional[dict]:
        """Get camera information from database."""
        try:
            from vigil.database.manager import get_camera_db
            db = get_camera_db()
            return db.get_camera(camera_id)
        except Exception as e:
            self.logger.error(f"Error getting camera info: {e}")
            return None
    
    def open_source(self, source: str) -> bool:
        """
        Open a video source (camera IP, file path, or camera index).
        
        Args:
            source: Video source (URL, file path, or camera index)
            
        Returns:
            True if source opened successfully, False otherwise
        """
        try:
            if self.cap and self.cap.isOpened():
                self.close_source()
            
            # Determine source type and open accordingly
            if isinstance(source, str) and source.startswith(('http://', 'https://', 'rtsp://')):
                # IP camera or stream
                self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                self.logger.info(f"Opening IP camera/stream: {source}")
            elif isinstance(source, str) and source.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                # Video file
                self.cap = cv2.VideoCapture(source)
                self.logger.info(f"Opening video file: {source}")
            elif isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
                # Camera index
                camera_idx = int(source) if isinstance(source, str) else source
                self.cap = cv2.VideoCapture(camera_idx)
                self.logger.info(f"Opening camera index: {camera_idx}")
            else:
                # Try as string (could be camera index as string)
                self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                self.logger.info(f"Opening source as string: {source}")
            
            if not self.cap.isOpened():
                raise CameraError(f"Failed to open video source: {source}")
            
            # Get video properties
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            if self.fps <= 0:
                self.fps = 30  # Default FPS
            
            self.current_source = source
            self.logger.info(f"Video source opened: {source} ({self.width}x{self.height} @ {self.fps} FPS)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening video source {source}: {e}")
            raise CameraError(f"Failed to open video source: {e}")
    
    def close_source(self) -> None:
        """Close the current video source."""
        if self.cap:
            self.stop_capture()
            self.cap.release()
            self.cap = None
            self.current_source = None
            self.logger.info("Video source closed")
    
    def start_capture(self, frame_callback: Callable) -> bool:
        """
        Start continuous frame capture.
        
        Args:
            frame_callback: Function to call with each frame
            
        Returns:
            True if capture started successfully, False otherwise
        """
        if not self.cap or not self.cap.isOpened():
            raise CameraError("No video source is open")
        
        if self.is_running:
            self.logger.warning("Capture is already running")
            return True
        
        self.frame_callback = frame_callback
        self.is_running = True
        self.frame_count = 0
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.logger.info("Frame capture started")
        return True
    
    def stop_capture(self) -> None:
        """Stop continuous frame capture."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        self.capture_thread = None
        self.frame_callback = None
        
        self.logger.info("Frame capture stopped")
    
    def _capture_loop(self) -> None:
        """Main capture loop running in separate thread."""
        last_frame_time = time.time()
        frame_interval = 1.0 / self.fps if self.fps > 0 else 1.0 / 30.0
        
        while self.is_running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    # End of video file or camera disconnect
                    if self.camera_mode == '1':  # Test mode (video file)
                        self.logger.info("End of video file reached")
                        break
                    else:
                        self.logger.warning("Failed to read frame, attempting reconnection...")
                        time.sleep(1.0)
                        continue
                
                # Frame rate limiting
                current_time = time.time()
                if current_time - last_frame_time >= frame_interval:
                    if self.frame_callback:
                        self.frame_callback(frame)
                    
                    self.frame_count += 1
                    last_frame_time = current_time
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)
                continue
        
        self.is_running = False
    
    def read_frame(self) -> Optional[Tuple[bool, any]]:
        """
        Read a single frame from the video source.
        
        Returns:
            Tuple of (success, frame) or None if no source
        """
        if not self.cap or not self.cap.isOpened():
            return None
        
        try:
            ret, frame = self.cap.read()
            return ret, frame
        except Exception as e:
            self.logger.error(f"Error reading frame: {e}")
            return False, None
    
    def get_frame_size(self) -> Tuple[int, int]:
        """Get current frame dimensions."""
        return self.width, self.height
    
    def get_fps(self) -> float:
        """Get current FPS."""
        return self.fps
    
    def get_frame_count(self) -> int:
        """Get total frame count (for video files)."""
        if not self.cap or not self.cap.isOpened():
            return 0
        
        try:
            return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        except:
            return 0
    
    def set_resolution(self, width: int, height: int) -> bool:
        """Set video resolution."""
        if not self.cap or not self.cap.isOpened():
            return False
        
        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Update stored dimensions
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self.logger.info(f"Resolution set to {self.width}x{self.height}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting resolution: {e}")
            return False
    
    def is_opened(self) -> bool:
        """Check if video source is open."""
        return self.cap is not None and self.cap.isOpened()
    
    def get_source_info(self) -> dict:
        """Get information about the current video source."""
        return {
            'source': self.current_source,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'frame_count': self.get_frame_count(),
            'is_running': self.is_running,
            'frames_captured': self.frame_count
        }


# Global video capture instance
video_capture = VideoCapture()

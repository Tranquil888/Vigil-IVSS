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
        
        # Video file tracking
        self.is_video_file = False
        self.total_frames = 0
        self.current_frame = 0
        self.frame_skip = 0
        self.frame_counter = 0
        
        # FPS tracking for accurate display
        self.actual_capture_fps = 0
        self.last_fps_calc_time = 0
        self.frames_since_last_calc = 0
        
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
            self.is_video_file = False
            if isinstance(source, str) and source.startswith(('http://', 'https://', 'rtsp://')):
                # IP camera or stream
                self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                self.logger.info(f"Opening IP camera/stream: {source}")
            elif isinstance(source, str) and source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv')):
                # Video file
                self.cap = cv2.VideoCapture(source)
                self.is_video_file = True
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
            
            # Get total frame count for video files
            if self.is_video_file:
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.current_frame = 0
                
                # Calculate video duration for debugging
                duration_seconds = self.total_frames / self.fps if self.fps > 0 else 0
                self.logger.info(f"Video info: {self.total_frames} frames, {self.fps:.2f} FPS, {duration_seconds:.2f} seconds duration")
            else:
                self.total_frames = 0
                self.current_frame = 0
            
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
        
        # Get FPS setting from settings database
        try:
            max_fps = int(settings.get_setting('camera_max_fps', '30'))
        except (ValueError, TypeError):
            max_fps = 30
        
        # Get video playback settings
        loop_playback = settings.get_setting('video_loop_playback', '0') == '1'
        video_speed_multiplier = float(settings.get_setting('video_playback_speed', '1.0'))
        
        # For video files, calculate frame skipping to reduce CPU load
        if self.is_video_file:
            native_fps = self.fps if self.fps > 0 else 30.0
            # Skip frames for high FPS videos to reduce CPU load
            if native_fps > 30:
                self.frame_skip = 2  # Process every 2nd frame
            elif native_fps > 20:
                self.frame_skip = 1  # Process every frame
            else:
                self.frame_skip = 0  # Process every frame for low FPS
            self.frame_counter = 0
            self.logger.info(f"Video frame skipping: Native FPS={native_fps}, Skip every {self.frame_skip + 1} frames")
            
            # Apply speed multiplier using OpenCV's playback speed property
            # This is the correct way to control video playback speed
            if self.cap and hasattr(self.cap, 'set'):
                # OpenCV v4.5+ supports CAP_PROP_POS_MSEC for better timing
                # For now, we'll use frame skipping approach
                pass
        else:
            self.frame_skip = 0
            self.frame_counter = 0
        
        # Use camera's native FPS if it's lower than max FPS
        # For video files, use the video's native FPS to maintain proper playback speed
        if self.is_video_file:
            native_fps = self.fps if self.fps > 0 else 30.0
            # Speed multiplier: 0.25 = quarter speed, 0.5 = half speed, 1.0 = normal, 2.0 = double speed
            effective_fps = native_fps * video_speed_multiplier
            self.logger.info(f"Video file detected - Native FPS: {native_fps}, Speed multiplier: {video_speed_multiplier}, Effective FPS: {effective_fps}")
        else:
            effective_fps = min(max_fps, self.fps) if self.fps > 0 else max_fps
            self.logger.info(f"Camera detected - Native FPS: {self.fps}, Max FPS: {max_fps}, Effective FPS: {effective_fps}")
        
        frame_interval = 1.0 / effective_fps if effective_fps > 0 else 1.0 / 30.0
        
        self.logger.info(f"Using FPS: {effective_fps} (camera: {self.fps}, max: {max_fps})")
        
        while self.is_running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    # End of video file or camera disconnect
                    if self.is_video_file:
                        self.logger.info("End of video file reached")
                        
                        if loop_playback and self.is_running:
                            # Reset video to beginning
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            self.current_frame = 0
                            self.logger.info("Looping video playback")
                            continue
                        else:
                            # Video ended, stop capture
                            self.logger.info("Video file completed, stopping capture")
                            break
                    else:
                        # Camera disconnect - try to reconnect
                        self.logger.warning("Failed to read frame, attempting reconnection...")
                        time.sleep(1.0)
                        continue
                
                # For video files, use proper frame duration timing
                # For cameras, apply frame rate limiting
                if self.is_video_file:
                    self.frame_counter += 1
                    
                    # Apply frame skipping to reduce CPU load
                    if self.frame_counter % (self.frame_skip + 1) == 0:
                        # Process video frame with proper timing
                        if self.frame_callback:
                            self.frame_callback(frame)
                        
                        self.frame_count += 1
                        self.frames_since_last_calc += 1
                        self.current_frame += 1
                        
                        # Calculate actual FPS every second
                        current_time = time.time()
                        if self.last_fps_calc_time == 0:
                            self.last_fps_calc_time = current_time
                        elif current_time - self.last_fps_calc_time >= 1.0:
                            self.actual_capture_fps = self.frames_since_last_calc
                            self.frames_since_last_calc = 0
                            self.last_fps_calc_time = current_time
                        
                        # Control playback speed with frame delay for ALL speeds including 1x
                        # For 0.5x speed, wait 2x longer between frames
                        # For 0.25x speed, wait 4x longer between frames
                        # For 1.0x speed, wait normal time between frames
                        if self.fps > 0:
                            delay_factor = 1.0 / video_speed_multiplier
                            frame_delay = (1.0 / self.fps) * delay_factor
                            time.sleep(max(0.001, frame_delay))
                    else:
                        # Still need to track frame position for progress
                        self.current_frame += 1
                else:
                    # Frame rate limiting for cameras
                    current_time = time.time()
                    if current_time - last_frame_time >= frame_interval:
                        if self.frame_callback:
                            self.frame_callback(frame)
                        
                        self.frame_count += 1
                        self.frames_since_last_calc += 1
                        self.current_frame += 1
                        last_frame_time = current_time
                        
                        # Calculate actual FPS every second
                        if self.last_fps_calc_time == 0:
                            self.last_fps_calc_time = current_time
                        elif current_time - self.last_fps_calc_time >= 1.0:
                            self.actual_capture_fps = self.frames_since_last_calc
                            self.frames_since_last_calc = 0
                            self.last_fps_calc_time = current_time
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)
                continue
        
        self.is_running = False
        self.logger.info("Capture loop ended")
    
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
            'actual_fps': self.actual_capture_fps,  # Real capture rate
            'frame_count': self.get_frame_count(),
            'is_running': self.is_running,
            'frames_captured': self.frame_count
        }
    
    def get_actual_fps(self) -> float:
        """Get the actual capture FPS (not camera's reported FPS)."""
        return self.actual_capture_fps
    
    def is_video_file_source(self) -> bool:
        """Check if current source is a video file."""
        return self.is_video_file
    
    def get_video_progress(self) -> dict:
        """Get video file progress information."""
        if not self.is_video_file or self.total_frames <= 0:
            return {
                'is_video_file': False,
                'current_frame': 0,
                'total_frames': 0,
                'progress_percent': 0.0
            }
        
        progress_percent = (self.current_frame / self.total_frames) * 100.0 if self.total_frames > 0 else 0.0
        
        return {
            'is_video_file': True,
            'current_frame': self.current_frame,
            'total_frames': self.total_frames,
            'progress_percent': progress_percent
        }
    
    def seek_to_frame(self, frame_number: int) -> bool:
        """Seek to a specific frame in video file."""
        if not self.is_video_file or not self.cap or not self.cap.isOpened():
            return False
        
        try:
            if frame_number >= 0 and frame_number < self.total_frames:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                self.current_frame = frame_number
                self.logger.info(f"Seeked to frame {frame_number}")
                return True
            else:
                self.logger.warning(f"Invalid frame number: {frame_number}")
                return False
        except Exception as e:
            self.logger.error(f"Error seeking to frame {frame_number}: {e}")
            return False


# Global video capture instance
video_capture = VideoCapture()

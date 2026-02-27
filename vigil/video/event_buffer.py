"""
Event video buffer management for Vigil surveillance system.
Captures 10-second video clips at the start of events.
"""

import cv2
import os
import time
import threading
from datetime import datetime
from queue import Queue, Empty
from typing import Optional, List
from vigil.utils.logging_config import get_video_logger
from vigil.config.constants import get_data_dir


class EventVideoBuffer:
    """Manages circular buffer of video frames for event capture."""
    
    def __init__(self, buffer_duration: int = 10, fps: int = 10):
        """
        Initialize video buffer.
        
        Args:
            buffer_duration: Duration in seconds to keep in buffer
            fps: Target FPS for saved video
        """
        self.logger = get_video_logger()
        self.buffer_duration = buffer_duration
        self.target_fps = fps
        
        # Buffer storage - keep frames for context
        self.frame_queue = Queue(maxsize=buffer_duration * fps)
        self.is_recording = False
        self.recording_lock = threading.Lock()
        
        # Recording state
        self.recording_frames = []
        self.recording_start_time = None
        self.recording_session_id = None
        
        # Video storage directory
        self.video_dir = os.path.join(get_data_dir(), 'event_videos')
        os.makedirs(self.video_dir, exist_ok=True)
        
        # Statistics
        self.frames_captured = 0
        self.videos_saved = 0
        
        self.logger.info(f"EventVideoBuffer initialized: {buffer_duration}s at {fps} FPS")
    
    def add_frame(self, frame: cv2.Mat, timestamp: Optional[float] = None) -> None:
        """
        Add a frame to the circular buffer.
        
        Args:
            frame: Video frame
            timestamp: Frame timestamp (uses current time if None)
        """
        if timestamp is None:
            timestamp = time.time()
        
        frame_data = {
            'frame': frame.copy(),
            'timestamp': timestamp
        }
        
        # Add to queue (removes oldest if full)
        try:
            self.frame_queue.put_nowait(frame_data)
            self.frames_captured += 1
        except:
            # Queue is full, remove oldest and add new
            try:
                self.frame_queue.get_nowait()
                self.frame_queue.put_nowait(frame_data)
            except Empty:
                pass
        
        # If currently recording, add to recording frames
        if self.is_recording and self.recording_session_id is not None:
            self.recording_frames.append(frame_data)
            
            # Check if we have recorded enough frames
            recording_duration = timestamp - self.recording_start_time
            if recording_duration >= self.buffer_duration:
                # Stop recording and save video
                self._finish_recording()
    
    def start_event_capture(self, session_id: int, event_start_time: str) -> Optional[str]:
        """
        Start capturing video for an event.
        
        Args:
            session_id: Event session ID
            event_start_time: Event start timestamp string
            
        Returns:
            Path to saved video file, or None if failed
        """
        with self.recording_lock:
            if self.is_recording:
                self.logger.warning("Already recording, skipping new event")
                return None
            
            self.is_recording = True
            self.recording_session_id = session_id
            self.recording_start_time = time.time()
            self.recording_frames = []
        
        self.logger.info(f"Started recording for event {session_id}")
        return None  # Video will be saved when duration is reached
    
    def _finish_recording(self) -> None:
        """Finish recording and save video."""
        if not self.recording_frames or self.recording_session_id is None:
            return
        
        try:
            session_id = self.recording_session_id
            event_start_time = datetime.fromtimestamp(self.recording_start_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Sort frames by timestamp
            self.recording_frames.sort(key=lambda x: x['timestamp'])
            
            # Calculate video properties
            height, width = self.recording_frames[0]['frame'].shape[:2]
            
            # Generate video filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"event_{session_id:05d}_{timestamp}.mp4"
            video_path = os.path.join(self.video_dir, filename)
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                video_path, 
                fourcc, 
                self.target_fps, 
                (width, height)
            )
            
            if not out.isOpened():
                self.logger.error("Failed to create video writer")
                return
            
            # Write frames
            frames_written = 0
            start_time = self.recording_frames[0]['timestamp']
            end_time = self.recording_frames[-1]['timestamp']
            
            for frame_data in self.recording_frames:
                out.write(frame_data['frame'])
                frames_written += 1
            
            out.release()
            
            # Get file size
            file_size = os.path.getsize(video_path)
            
            # Calculate duration
            duration = int(end_time - start_time)
            
            self.logger.info(f"Saved event video: {filename} ({frames_written} frames, {duration}s, {file_size} bytes)")
            
            # Store in database
            self._store_video_record(session_id, video_path, event_start_time, 
                                   datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S"),
                                   duration, file_size)
            
            self.videos_saved += 1
            
        except Exception as e:
            self.logger.error(f"Error saving event video: {e}")
        finally:
            # Reset recording state
            with self.recording_lock:
                self.is_recording = False
                self.recording_frames = []
                self.recording_start_time = None
                self.recording_session_id = None
    
    def _store_video_record(self, session_id: int, video_path: str, start_time: str,
                           end_time: str, duration: int, file_size: int) -> None:
        """Store video record in database."""
        try:
            from vigil.database.manager import get_events_db
            db = get_events_db()
            
            video_id = db.add_event_video(
                session_id, video_path, start_time, end_time, duration, file_size
            )
            
            self.logger.info(f"Stored video record: ID {video_id} for session {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing video record: {e}")
    
    def get_buffer_info(self) -> dict:
        """Get buffer statistics."""
        return {
            'frames_in_buffer': self.frame_queue.qsize(),
            'max_frames': self.frame_queue.maxsize,
            'frames_captured': self.frames_captured,
            'videos_saved': self.videos_saved,
            'is_recording': self.is_recording
        }
    
    def clear_buffer(self) -> None:
        """Clear all frames from buffer."""
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break
        self.logger.info("Video buffer cleared")


# Global video buffer instance
event_video_buffer = EventVideoBuffer()

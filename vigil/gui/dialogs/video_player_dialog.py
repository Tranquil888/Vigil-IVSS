"""
Video player dialog for Vigil surveillance system.
Custom video player with playback controls for event videos.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import threading
import time
from PIL import Image, ImageTk
from typing import Optional, Dict, Any
from vigil.utils.logging_config import get_ui_logger


class VideoPlayerDialog:
    """Custom video player dialog with playback controls."""
    
    def __init__(self, parent, video_path: str, title: str = "Event Video Player"):
        """
        Initialize video player dialog.
        
        Args:
            parent: Parent window
            video_path: Path to video file
            title: Window title
        """
        self.parent = parent
        self.video_path = video_path
        self.logger = get_ui_logger()
        
        # Video state
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_playing = False
        self.is_paused = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30.0
        self.duration = 0.0
        self.video_width = 640
        self.video_height = 480
        
        # Playback control
        self.playback_thread: Optional[threading.Thread] = None
        self.stop_playback = threading.Event()
        self.video_speed = 1.0
        
        # UI elements
        self.video_label: Optional[tk.Label] = None
        self.progress_var = tk.DoubleVar()
        self.time_var = tk.StringVar(value="00:00 / 00:00")
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Initialize video
        if not self._load_video():
            self.dialog.destroy()
            return
        
        # Create UI
        self._create_widgets()
        
        # Handle window closing
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Center dialog on parent
        self._center_dialog()
        
        self.logger.info(f"Video player opened: {video_path}")
    
    def _load_video(self) -> bool:
        """Load video file and get properties."""
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            
            if not self.cap.isOpened():
                messagebox.showerror("Error", f"Cannot open video file: {self.video_path}")
                return False
            
            # Get video properties
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate duration
            if self.fps > 0:
                self.duration = self.total_frames / self.fps
            
            self.logger.info(f"Video loaded: {self.video_width}x{self.video_height}, "
                           f"{self.total_frames} frames, {self.fps:.2f} FPS, {self.duration:.2f}s")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading video: {e}")
            messagebox.showerror("Error", f"Failed to load video: {e}")
            return False
    
    def _create_widgets(self) -> None:
        """Create video player UI widgets."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.dialog.rowconfigure(0, weight=1)
        self.dialog.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Video display area
        video_frame = ttk.Frame(main_frame, relief="sunken", borderwidth=2)
        video_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        self.video_label = tk.Label(video_frame, bg="black")
        self.video_label.pack(expand=True, fill="both")
        
        # Progress bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Scale(
            progress_frame, 
            from_=0, 
            to=100,
            variable=self.progress_var,
            command=self._on_progress_change,
            length=400
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.time_label = ttk.Label(progress_frame, textvariable=self.time_var)
        self.time_label.grid(row=0, column=1)
        
        # Control buttons
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=2, column=0, sticky="ew")
        
        # Playback controls
        self.play_button = ttk.Button(
            controls_frame, 
            text="▶ Play", 
            command=self._toggle_playback,
            width=10
        )
        self.play_button.grid(row=0, column=0, padx=5)
        
        ttk.Button(
            controls_frame, 
            text="⏮", 
            command=self._seek_backward,
            width=5
        ).grid(row=0, column=1, padx=2)
        
        ttk.Button(
            controls_frame, 
            text="⏭", 
            command=self._seek_forward,
            width=5
        ).grid(row=0, column=2, padx=2)
        
        ttk.Button(
            controls_frame, 
            text="⏹ Stop", 
            command=self._stop_playback,
            width=8
        ).grid(row=0, column=3, padx=5)
        
        # Speed control
        ttk.Label(controls_frame, text="Speed:").grid(row=0, column=4, padx=(20, 5))
        
        self.speed_var = tk.StringVar(value="1.0x")
        speed_combo = ttk.Combobox(
            controls_frame, 
            textvariable=self.speed_var,
            values=["0.5x", "0.75x", "1.0x", "1.5x", "2.0x", "3.0x"],
            width=8,
            state="readonly"
        )
        speed_combo.grid(row=0, column=5, padx=5)
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)
        
        # Volume control (placeholder)
        ttk.Label(controls_frame, text="Volume:").grid(row=0, column=6, padx=(20, 5))
        ttk.Scale(
            controls_frame,
            from_=0,
            to=100,
            orient="horizontal",
            length=100,
            state="disabled"
        ).grid(row=0, column=7, padx=5)
        
        # Display first frame
        self._display_frame(0)
    
    def _center_dialog(self) -> None:
        """Center dialog on parent window."""
        self.dialog.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _toggle_playback(self) -> None:
        """Toggle between play and pause."""
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()
    
    def _start_playback(self) -> None:
        """Start video playback."""
        if self.is_playing:
            return
        
        self.is_playing = True
        self.is_paused = False
        self.stop_playback.clear()
        
        self.play_button.config(text="⏸ Pause")
        
        # Start playback thread
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()
        
        self.logger.info("Video playback started")
    
    def _pause_playback(self) -> None:
        """Pause video playback."""
        if not self.is_playing:
            return
        
        self.is_playing = False
        self.is_paused = True
        self.stop_playback.set()
        
        self.play_button.config(text="▶ Play")
        
        self.logger.info("Video playback paused")
    
    def _stop_playback(self) -> None:
        """Stop video playback and reset to beginning."""
        self.is_playing = False
        self.is_paused = False
        self.stop_playback.set()
        
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)
        
        # Reset to first frame
        self.current_frame = 0
        self._display_frame(0)
        self._update_progress()
        
        self.play_button.config(text="▶ Play")
        
        self.logger.info("Video playback stopped")
    
    def _playback_worker(self) -> None:
        """Worker thread for video playback."""
        frame_delay = 1.0 / (self.fps * self.video_speed)
        
        while not self.stop_playback.is_set() and self.current_frame < self.total_frames:
            start_time = time.time()
            
            # Display current frame
            self._display_frame(self.current_frame)
            self._update_progress()
            
            # Move to next frame
            self.current_frame += 1
            
            # Calculate delay for proper playback speed
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_delay - elapsed)
            
            if sleep_time > 0:
                self.stop_playback.wait(sleep_time)
        
        # Playback finished
        if self.current_frame >= self.total_frames:
            self.dialog.after(0, self._playback_finished)
    
    def _display_frame(self, frame_number: int) -> None:
        """Display a specific frame."""
        if not self.cap or frame_number < 0 or frame_number >= self.total_frames:
            return
        
        try:
            # Set frame position
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = self.cap.read()
            if not ret:
                return
            
            # Convert color space (BGR to RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame to fit display
            display_width = self.video_label.winfo_width()
            display_height = self.video_label.winfo_height()
            
            if display_width > 1 and display_height > 1:
                # Calculate aspect ratio
                aspect_ratio = self.video_width / self.video_height
                
                if display_width / display_height > aspect_ratio:
                    new_height = display_height
                    new_width = int(display_height * aspect_ratio)
                else:
                    new_width = display_width
                    new_height = int(display_width / aspect_ratio)
                
                frame_rgb = cv2.resize(frame_rgb, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Convert to PIL Image and then to PhotoImage
            image = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image)
            
            # Update label
            self.video_label.config(image=photo)
            self.video_label.image = photo  # Keep reference
            
        except Exception as e:
            self.logger.error(f"Error displaying frame {frame_number}: {e}")
    
    def _update_progress(self) -> None:
        """Update progress bar and time display."""
        if self.total_frames > 0:
            progress = (self.current_frame / self.total_frames) * 100
            self.progress_var.set(progress)
            
            current_time = self.current_frame / self.fps
            self.time_var.set(f"{self._format_time(current_time)} / {self._format_time(self.duration)}")
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to MM:SS format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _on_progress_change(self, value: float) -> None:
        """Handle progress bar change."""
        if self.total_frames > 0:
            new_frame = int((float(value) / 100) * self.total_frames)
            new_frame = max(0, min(new_frame, self.total_frames - 1))
            
            if not self.is_playing:
                self.current_frame = new_frame
                self._display_frame(new_frame)
                self._update_progress()
    
    def _seek_backward(self) -> None:
        """Seek backward by 5 seconds."""
        seek_frames = int(5 * self.fps)
        new_frame = max(0, self.current_frame - seek_frames)
        
        if not self.is_playing:
            self.current_frame = new_frame
            self._display_frame(new_frame)
            self._update_progress()
    
    def _seek_forward(self) -> None:
        """Seek forward by 5 seconds."""
        seek_frames = int(5 * self.fps)
        new_frame = min(self.total_frames - 1, self.current_frame + seek_frames)
        
        if not self.is_playing:
            self.current_frame = new_frame
            self._display_frame(new_frame)
            self._update_progress()
    
    def _on_speed_change(self, event) -> None:
        """Handle playback speed change."""
        speed_text = self.speed_var.get()
        self.video_speed = float(speed_text.replace('x', ''))
        self.logger.info(f"Playback speed changed to {self.video_speed}x")
    
    def _playback_finished(self) -> None:
        """Handle playback completion."""
        self.is_playing = False
        self.play_button.config(text="▶ Play")
        self.logger.info("Video playback finished")
    
    def _on_closing(self) -> None:
        """Handle dialog closing."""
        self._stop_playback()
        
        if self.cap:
            self.cap.release()
        
        self.dialog.grab_release()
        self.dialog.destroy()
        
        self.logger.info("Video player closed")

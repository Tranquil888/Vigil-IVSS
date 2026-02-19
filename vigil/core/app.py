"""
Main application controller for Vigil surveillance system.
"""

import tkinter as tk
from typing import Optional
from vigil.utils.logging_config import get_main_logger
from vigil.config.settings import settings
from vigil.gui.main_window import MainWindow
from vigil.recognition.training_service import training_service


class VigilApp:
    """Main application controller that coordinates all system components."""
    
    def __init__(self):
        self.logger = get_main_logger()
        self.root: Optional[tk.Tk] = None
        self.is_running = False
        self.current_user = None
        self.current_user_role = None
        self.main_window = None
        
        self.logger.info("Initializing Vigil application")
    
    def initialize(self) -> bool:
        """Initialize the application and all its components."""
        try:
            # Load application settings
            self._load_settings()
            
            # Initialize training service
            self._initialize_training_service()
            
            # Initialize main window
            self._create_main_window()
            
            self.logger.info("Application initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            return False
    
    def _load_settings(self) -> None:
        """Load application settings."""
        try:
            # Load time format setting
            time_format = settings.get_setting('time_format', '1')
            self.logger.info(f"Time format setting loaded: {time_format}")
            
            # Load other essential settings
            self.logger.info("Application settings loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
    
    def _initialize_training_service(self) -> None:
        """Initialize the training service."""
        try:
            # Training service is automatically initialized on import
            # Just verify it's working
            status = training_service.get_training_status()
            self.logger.info(f"Training service initialized: {status}")
            
        except Exception as e:
            self.logger.error(f"Error initializing training service: {e}")
    
    def _create_main_window(self) -> None:
        """Create the main application window."""
        self.root = tk.Tk()
        self.root.title("Vigil - Intelligent Video Surveillance System")
        
        # Set minimum window size
        self.root.minsize(800, 600)
        
        # Center window on screen
        self._center_window()
        
        # Setup window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create main window GUI
        self.main_window = MainWindow(self.root)
        
        self.logger.info("Main window created")
    
    def _center_window(self) -> None:
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def start(self) -> None:
        """Start the application main loop."""
        if not self.root:
            raise RuntimeError("Application not initialized")
        
        self.is_running = True
        self.logger.info("Starting application main loop")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        finally:
            self.is_running = False
            self.logger.info("Application stopped")
    
    def stop(self) -> None:
        """Stop the application."""
        if self.root and self.is_running:
            self.logger.info("Stopping application")
            
            # Stop training service if active
            try:
                status = training_service.get_training_status()
                if status.get('is_training'):
                    training_service.stop_training()
                    self.logger.info("Stopped training service")
            except Exception as e:
                self.logger.error(f"Error stopping training service: {e}")
            
            self.root.quit()
    
    def on_closing(self) -> None:
        """Handle window closing event."""
        self.logger.info("Window closing event triggered")
        self.stop()
    
    def set_current_user(self, username: str, role: str) -> None:
        """Set the currently authenticated user."""
        self.current_user = username
        self.current_user_role = role
        self.logger.info(f"User authenticated: {username} ({role})")
    
    def clear_current_user(self) -> None:
        """Clear the current user session."""
        self.current_user = None
        self.current_user_role = None
        self.logger.info("User session cleared")
    
    def is_user_authenticated(self) -> bool:
        """Check if a user is currently authenticated."""
        return self.current_user is not None
    
    def get_current_user(self) -> Optional[tuple]:
        """Get the current user information."""
        if self.current_user:
            return (self.current_user, self.current_user_role)
        return None


# Global application instance
app = VigilApp()

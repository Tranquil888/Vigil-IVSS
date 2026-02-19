"""
Main application window for Vigil surveillance system.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
from typing import Optional
from vigil.gui.dialogs.auth_dialog import AuthenticationDialog
from vigil.gui.dialogs.training_dialog import TrainingDialog
from vigil.auth.authorization import authz_manager
from vigil.utils.logging_config import get_ui_logger
from vigil.video.capture import video_capture
from vigil.video.processing import frame_processor
from vigil.recognition.face_detector import face_detector
from vigil.recognition.training_service import training_service
from vigil.events.logger import event_logger


class MainWindow:
    """Main application window."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = get_ui_logger()
        self.current_user = None
        self.current_role = None
        self.is_camera_running = False
        self.is_recording = False
        self.is_streaming = False
        self.current_frame = None
        
        self._setup_window()
        self._create_widgets()
        
        # Show authentication dialog on startup
        self.root.after(100, self._authenticate_user)
    
    def _setup_window(self) -> None:
        """Setup the main window properties."""
        self.root.title("Vigil - Intelligent Video Surveillance System")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self) -> None:
        """Create main window widgets."""
        # Create menu bar
        self._create_menu_bar()
        
        # Create main toolbar
        self._create_toolbar()
        
        # Create status bar
        self._create_status_bar()
        
        # Create main content area
        self._create_content_area()
    
    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self._on_closing)
        
        # Users menu (admin only)
        self.users_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Users", menu=self.users_menu)
        self.users_menu.add_command(label="Create User", command=self._create_user)
        self.users_menu.add_command(label="User List", command=self._user_list)
        
        # Objects menu
        objects_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Objects", menu=objects_menu)
        objects_menu.add_command(label="Add Object", command=self._add_object)
        objects_menu.add_command(label="Object List", command=self._object_list)
        objects_menu.add_command(label="Train Model", command=self._train_model)
        
        # Camera menu
        camera_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Camera", menu=camera_menu)
        camera_menu.add_command(label="Camera Settings", command=self._camera_settings)
        
        # Video menu
        video_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Video", menu=video_menu)
        video_menu.add_command(label="Start Recording", command=self._start_recording)
        video_menu.add_command(label="Stop Recording", command=self._stop_recording)
        video_menu.add_command(label="Start Streaming", command=self._start_streaming)
        video_menu.add_command(label="Stop Streaming", command=self._stop_streaming)
        
        # Events menu
        events_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Events", menu=events_menu)
        events_menu.add_command(label="View Events", command=self._view_events)
        events_menu.add_command(label="Export Events", command=self._export_events)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="System Settings", command=self._system_settings)
        
        # Initially disable admin-only menus
        self._update_menu_permissions()
    
    def _create_toolbar(self) -> None:
        """Create the main toolbar."""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side='top', fill='x', padx=5, pady=2)
        
        # User info label
        self.user_label = ttk.Label(toolbar, text="Not authenticated")
        self.user_label.pack(side='right', padx=5)
        
        # Quick action buttons
        ttk.Button(toolbar, text="Start Camera", command=self._start_camera).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Stop Camera", command=self._stop_camera).pack(side='left', padx=2)
        ttk.Separator(toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        ttk.Button(toolbar, text="Start Recording", command=self._start_recording).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Stop Recording", command=self._stop_recording).pack(side='left', padx=2)
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side='bottom', fill='x')
        
        self.status_label = ttk.Label(self.status_bar, text="Ready", relief='sunken')
        self.status_label.pack(side='left', fill='x', expand=True, padx=2, pady=2)
        
        # Time label
        from time import strftime
        def update_time():
            time_str = strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.config(text=time_str)
            self.root.after(1000, update_time)
        
        self.time_label = ttk.Label(self.status_bar, text="", relief='sunken', width=20)
        self.time_label.pack(side='right', padx=2, pady=2)
        update_time()
    
    def _create_content_area(self) -> None:
        """Create the main content area."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Camera tab
        self.camera_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.camera_frame, text="Camera")
        self._create_camera_tab()
        
        # Events tab
        self.events_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.events_frame, text="Events")
        self._create_events_tab()
        
        # Objects tab
        self.objects_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.objects_frame, text="Objects")
        self._create_objects_tab()
    
    def _create_camera_tab(self) -> None:
        """Create the camera monitoring tab."""
        # Video display area
        video_frame = ttk.LabelFrame(self.camera_frame, text="Video Feed")
        video_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create canvas for video display
        self.video_canvas = tk.Canvas(
            video_frame,
            background='black',
            highlightthickness=0
        )
        self.video_canvas.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Camera controls
        controls_frame = ttk.Frame(self.camera_frame)
        controls_frame.pack(fill='x', padx=5, pady=5)
        
        self.start_camera_btn = ttk.Button(
            controls_frame, 
            text="Start Camera", 
            command=self._start_camera
        )
        self.start_camera_btn.pack(side='left', padx=2)
        
        self.stop_camera_btn = ttk.Button(
            controls_frame, 
            text="Stop Camera", 
            command=self._stop_camera,
            state='disabled'
        )
        self.stop_camera_btn.pack(side='left', padx=2)
        
        self.start_recording_btn = ttk.Button(
            controls_frame, 
            text="Start Recording", 
            command=self._start_recording
        )
        self.start_recording_btn.pack(side='left', padx=2)
        
        self.stop_recording_btn = ttk.Button(
            controls_frame, 
            text="Stop Recording", 
            command=self._stop_recording,
            state='disabled'
        )
        self.stop_recording_btn.pack(side='left', padx=2)
        
        # Recognition info
        info_frame = ttk.Frame(self.camera_frame)
        info_frame.pack(fill='x', padx=5, pady=5)
        
        self.recognition_label = ttk.Label(
            info_frame, 
            text="Recognition: Inactive",
            font=("Arial", 10)
        )
        self.recognition_label.pack(side='left', padx=5)
        
        self.fps_label = ttk.Label(
            info_frame, 
            text="FPS: 0",
            font=("Arial", 10)
        )
        self.fps_label.pack(side='right', padx=5)
    
    def _create_events_tab(self) -> None:
        """Create the events monitoring tab."""
        # Events list
        events_frame = ttk.LabelFrame(self.events_frame, text="Event Log")
        events_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create treeview for events
        columns = ("Time", "Event", "Object", "Confidence")
        self.events_tree = ttk.Treeview(events_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.events_tree.heading(col, text=col)
            self.events_tree.column(col, width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(events_frame, orient='vertical', command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=scrollbar.set)
        
        self.events_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Events controls
        events_controls = ttk.Frame(self.events_frame)
        events_controls.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(events_controls, text="Refresh", command=self._refresh_events).pack(side='left', padx=2)
        ttk.Button(events_controls, text="Export", command=self._export_events).pack(side='left', padx=2)
        ttk.Button(events_controls, text="Clear", command=self._clear_events).pack(side='left', padx=2)
    
    def _create_objects_tab(self) -> None:
        """Create the objects management tab."""
        # Objects list
        objects_frame = ttk.LabelFrame(self.objects_frame, text="Recognized Objects")
        objects_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create treeview for objects
        columns = ("Name", "Category", "Last Seen", "Confidence")
        self.objects_tree = ttk.Treeview(objects_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.objects_tree.heading(col, text=col)
            self.objects_tree.column(col, width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(objects_frame, orient='vertical', command=self.objects_tree.yview)
        self.objects_tree.configure(yscrollcommand=scrollbar.set)
        
        self.objects_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Objects controls
        objects_controls = ttk.Frame(self.objects_frame)
        objects_controls.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(objects_controls, text="Add Object", command=self._add_object).pack(side='left', padx=2)
        ttk.Button(objects_controls, text="Edit Object", command=self._edit_object).pack(side='left', padx=2)
        ttk.Button(objects_controls, text="Delete Object", command=self._delete_object).pack(side='left', padx=2)
        ttk.Separator(objects_controls, orient='vertical').pack(side='left', padx=5, fill='y')
        ttk.Button(objects_controls, text="Train Model", command=self._train_model).pack(side='left', padx=2)
    
    def _authenticate_user(self) -> None:
        """Show authentication dialog."""
        auth_dialog = AuthenticationDialog(self.root)
        result = auth_dialog.show()
        
        if result:
            username, role = result
            self.current_user = username
            self.current_role = role
            
            # Update UI
            self.user_label.config(text=f"{username} ({role})")
            self.status_label.config(text=f"Authenticated as {username}")
            self._update_menu_permissions()
            
            self.logger.info(f"User {username} ({role}) authenticated successfully")
        else:
            # Authentication failed or cancelled
            self.logger.warning("Authentication failed or cancelled")
            self.root.quit()
    
    def _update_menu_permissions(self) -> None:
        """Update menu permissions based on user role."""
        if not self.current_role:
            # Disable all menus when not authenticated
            self.users_menu.entryconfig("Create User", state='disabled')
            self.users_menu.entryconfig("User List", state='disabled')
            return
        
        # Enable/disable based on permissions
        can_manage_users = authz_manager.can_manage_users(self.current_role)
        self.users_menu.entryconfig("Create User", state='normal' if can_manage_users else 'disabled')
        self.users_menu.entryconfig("User List", state='normal' if can_manage_users else 'disabled')
    
    def _on_closing(self) -> None:
        """Handle window closing event."""
        if messagebox.askokcancel("Quit", "Do you want to quit Vigil?"):
            self.logger.info("Application closing")
            self.root.quit()
    
    # Menu command methods (placeholders for now)
    def _create_user(self) -> None:
        if not authz_manager.can_manage_users(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to manage users")
            return
        
        from vigil.gui.dialogs.auth_dialog import CreateUserDialog
        dialog = CreateUserDialog(self.root)
        dialog.show()
    
    def _user_list(self) -> None:
        if not authz_manager.can_manage_users(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to manage users")
            return
        messagebox.showinfo("User List", "User list feature coming soon")
    
    def _add_object(self) -> None:
        messagebox.showinfo("Add Object", "Add object feature coming soon")
    
    def _object_list(self) -> None:
        messagebox.showinfo("Object List", "Object list feature coming soon")
    
    def _train_model(self) -> None:
        if not authz_manager.can_train_model(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to train models")
            return
        
        try:
            # Show training dialog
            training_dialog = TrainingDialog(self.root)
            training_dialog.show()
            
        except Exception as e:
            self.logger.error(f"Error opening training dialog: {e}")
            messagebox.showerror("Error", f"Failed to open training dialog: {e}")
    
    def _camera_settings(self) -> None:
        if not authz_manager.can_manage_cameras(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to manage cameras")
            return
        messagebox.showinfo("Camera Settings", "Camera settings feature coming soon")
    
    def _start_recording(self) -> None:
        if not authz_manager.can_record_video(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to record video")
            return
        self.status_label.config(text="Recording started")
    
    def _stop_recording(self) -> None:
        if not authz_manager.can_record_video(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to record video")
            return
        self.status_label.config(text="Recording stopped")
    
    def _start_streaming(self) -> None:
        if not authz_manager.can_stream_video(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to stream video")
            return
        self.status_label.config(text="Streaming started")
    
    def _stop_streaming(self) -> None:
        if not authz_manager.can_stream_video(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to stream video")
            return
        self.status_label.config(text="Streaming stopped")
    
    def _view_events(self) -> None:
        if not authz_manager.can_view_events(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to view events")
            return
        messagebox.showinfo("View Events", "View events feature coming soon")
    
    def _export_events(self) -> None:
        if not authz_manager.can_export_events(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to export events")
            return
        messagebox.showinfo("Export Events", "Export events feature coming soon")
    
    def _system_settings(self) -> None:
        if not authz_manager.can_edit_settings(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to edit settings")
            return
        messagebox.showinfo("System Settings", "System settings feature coming soon")
    
    def _start_camera(self) -> None:
        """Start camera capture and processing."""
        if not authz_manager.can_stream_video(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to stream video")
            return
        
        try:
            # Get camera source from settings
            camera_source = video_capture.camera_link or 0  # Default to webcam if no camera configured
            
            # Open video source
            if video_capture.open_source(camera_source):
                # Start frame capture
                video_capture.start_capture(self._process_frame)
                
                self.is_camera_running = True
                self.status_label.config(text="Camera started")
                self.recognition_label.config(text="Recognition: Active")
                
                # Update button states
                self.start_camera_btn.config(state='disabled')
                self.stop_camera_btn.config(state='normal')
                
                # Log system event
                event_logger.log_system_event('camera_started', f'Camera started: {camera_source}')
                
                self.logger.info(f"Camera started with source: {camera_source}")
            else:
                messagebox.showerror("Error", "Failed to start camera")
                
        except Exception as e:
            self.logger.error(f"Error starting camera: {e}")
            messagebox.showerror("Error", f"Failed to start camera: {e}")
    
    def _stop_camera(self) -> None:
        """Stop camera capture."""
        try:
            video_capture.stop_capture()
            video_capture.close_source()
            
            self.is_camera_running = False
            self.status_label.config(text="Camera stopped")
            self.recognition_label.config(text="Recognition: Inactive")
            self.fps_label.config(text="FPS: 0")
            
            # Clear video canvas
            self.video_canvas.delete("all")
            
            # Update button states
            self.start_camera_btn.config(state='normal')
            self.stop_camera_btn.config(state='disabled')
            
            # Stop recording if active
            if self.is_recording:
                self._stop_recording()
            
            # Log system event
            event_logger.log_system_event('camera_stopped', 'Camera stopped')
            
            self.logger.info("Camera stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping camera: {e}")
    
    def _process_frame(self, frame) -> None:
        """Process video frame for display and recognition."""
        try:
            self.current_frame = frame.copy()
            
            # Perform face recognition if enabled
            if face_detector.is_trained():
                recognized_faces = face_detector.recognize_faces(frame)
                
                # Draw face boxes on frame
                frame = face_detector.draw_face_boxes(frame, recognized_faces)
                
                # Log recognition events
                for face in recognized_faces:
                    if face['name'] != 'Unknown':
                        event_logger.log_face_recognition(
                            face['name'], 
                            face['confidence'],
                            camera_source=str(video_capture.current_source)
                        )
                    else:
                        event_logger.log_unknown_face(
                            face['confidence'],
                            camera_source=str(video_capture.current_source)
                        )
            
            # Convert frame for display
            frame_rgb = frame_processor.convert_color_space(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame to fit canvas
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                frame_pil = Image.fromarray(frame_rgb)
                frame_pil.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage and display
                frame_photo = ImageTk.PhotoImage(frame_pil)
                
                # Keep reference to prevent garbage collection
                self.video_canvas.image = frame_photo
                
                # Center image on canvas
                self.video_canvas.delete("all")
                x = (canvas_width - frame_pil.width) // 2
                y = (canvas_height - frame_pil.height) // 2
                self.video_canvas.create_image(x, y, anchor='nw', image=frame_photo)
            
            # Update FPS display
            fps = video_capture.get_fps()
            self.fps_label.config(text=f"FPS: {fps:.1f}")
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
    
    def _start_recording(self) -> None:
        """Start video recording."""
        if not authz_manager.can_record_video(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to record video")
            return
        
        if not self.is_camera_running:
            messagebox.showwarning("Warning", "Please start camera first")
            return
        
        try:
            self.is_recording = True
            self.status_label.config(text="Recording started")
            
            # Update button states
            self.start_recording_btn.config(state='disabled')
            self.stop_recording_btn.config(state='normal')
            
            # Log system event
            event_logger.log_system_event('recording_started', 'Video recording started')
            
            self.logger.info("Recording started")
            
        except Exception as e:
            self.logger.error(f"Error starting recording: {e}")
            messagebox.showerror("Error", f"Failed to start recording: {e}")
    
    def _stop_recording(self) -> None:
        """Stop video recording."""
        try:
            self.is_recording = False
            self.status_label.config(text="Recording stopped")
            
            # Update button states
            self.start_recording_btn.config(state='normal')
            self.stop_recording_btn.config(state='disabled')
            
            # Log system event
            event_logger.log_system_event('recording_stopped', 'Video recording stopped')
            
            self.logger.info("Recording stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}")
    
    def _start_streaming(self) -> None:
        """Start web streaming."""
        if not authz_manager.can_stream_video(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to stream video")
            return
        
        try:
            self.is_streaming = True
            self.status_label.config(text="Streaming started")
            
            # Log system event
            event_logger.log_system_event('streaming_started', 'Web streaming started')
            
            self.logger.info("Streaming started")
            
        except Exception as e:
            self.logger.error(f"Error starting streaming: {e}")
            messagebox.showerror("Error", f"Failed to start streaming: {e}")
    
    def _stop_streaming(self) -> None:
        """Stop web streaming."""
        try:
            self.is_streaming = False
            self.status_label.config(text="Streaming stopped")
            
            # Log system event
            event_logger.log_system_event('streaming_stopped', 'Web streaming stopped')
            
            self.logger.info("Streaming stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping streaming: {e}")
    
    def _refresh_events(self) -> None:
        """Refresh events display."""
        try:
            # Clear existing events
            for item in self.events_tree.get_children():
                self.events_tree.delete(item)
            
            # Get recent events
            events = event_logger.get_recent_events(hours=24)
            
            for event in events:
                self.events_tree.insert('', 'end', values=(
                    event['timestamp'],
                    event['event_type'],
                    event['object_name'] or 'N/A',
                    f"{event['confidence']:.2f}" if event['confidence'] else 'N/A'
                ))
            
            self.status_label.config(text="Events refreshed")
            
        except Exception as e:
            self.logger.error(f"Error refreshing events: {e}")
            self.status_label.config(text="Error refreshing events")
    
    def _clear_events(self) -> None:
        """Clear events display."""
        if messagebox.askokcancel("Clear Events", "Clear all events from display?"):
            for item in self.events_tree.get_children():
                self.events_tree.delete(item)
            self.status_label.config(text="Events cleared")
    
    def _edit_object(self) -> None:
        messagebox.showinfo("Edit Object", "Edit object feature coming soon")
    
    def _delete_object(self) -> None:
        messagebox.showinfo("Delete Object", "Delete object feature coming soon")

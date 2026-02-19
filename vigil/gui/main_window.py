"""
Main application window for Vigil surveillance system.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import time
from typing import Optional
from vigil.gui.dialogs.auth_dialog import AuthenticationDialog
from vigil.gui.dialogs.training_dialog import TrainingDialog
from vigil.auth.authorization import authz_manager
from vigil.utils.logging_config import get_ui_logger
from vigil.video.capture import video_capture
from vigil.video.processing import frame_processor
from vigil.recognition.face_detector import face_detector
from vigil.gui.dialogs.object_dialogs import AddObjectDialog, EditObjectDialog, DeleteObjectDialog
from vigil.recognition.training_service import training_service
from vigil.events.logger import event_logger
from vigil.config.settings import settings


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
        self.recognition_enabled = True
        self.frame_count = 0
        self.last_recognition_frame = 0
        self.recognition_stats = {'total_faces': 0, 'recognized_faces': 0, 'unknown_faces': 0}
        self.last_recognition_time = {}
        
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
        objects_menu.add_command(label="Refresh Objects", command=self._refresh_objects_list)
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
        
        # Initialize objects list
        self._refresh_objects_list()
    
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
        
        # Recognition controls and info
        recognition_frame = ttk.LabelFrame(self.camera_frame, text="Face Recognition")
        recognition_frame.pack(fill='x', padx=5, pady=5)
        
        # Recognition controls row 1
        controls_row1 = ttk.Frame(recognition_frame)
        controls_row1.pack(fill='x', padx=5, pady=2)
        
        self.recognition_enabled_var = tk.BooleanVar(value=True)
        self.recognition_enabled_cb = ttk.Checkbutton(
            controls_row1,
            text="Enable Recognition",
            variable=self.recognition_enabled_var,
            command=self._toggle_recognition
        )
        self.recognition_enabled_cb.pack(side='left', padx=5)
        
        self.recognition_label = ttk.Label(
            controls_row1, 
            text="Recognition: Inactive",
            font=("Arial", 10, "bold")
        )
        self.recognition_label.pack(side='left', padx=10)
        
        self.fps_label = ttk.Label(
            controls_row1, 
            text="FPS: 0",
            font=("Arial", 10)
        )
        self.fps_label.pack(side='right', padx=5)
        
        # Recognition controls row 2
        controls_row2 = ttk.Frame(recognition_frame)
        controls_row2.pack(fill='x', padx=5, pady=2)
        
        self.face_count_label = ttk.Label(
            controls_row2,
            text="Faces: 0",
            font=("Arial", 9)
        )
        self.face_count_label.pack(side='left', padx=5)
        
        self.recognized_faces_label = ttk.Label(
            controls_row2,
            text="Recognized: None",
            font=("Arial", 9)
        )
        self.recognized_faces_label.pack(side='left', padx=10)
        
        self.recognition_stats_label = ttk.Label(
            controls_row2,
            text="Accuracy: 0%",
            font=("Arial", 9)
        )
        self.recognition_stats_label.pack(side='right', padx=5)
    
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
        columns = ("Name", "Category", "Phone", "Address", "Model Folder")
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
        """Add a new object."""
        try:
            dialog = AddObjectDialog(self.root)
            self.root.wait_window(dialog)
            
            if dialog.result:
                self._refresh_objects_list()
                self.logger.info(f"Added new object: {dialog.result.get_full_name()}")
                
        except Exception as e:
            self.logger.error(f"Error adding object: {e}")
            messagebox.showerror("Error", f"Failed to add object: {e}")
    
    def _edit_object(self) -> None:
        """Edit selected object."""
        try:
            selected = self.objects_tree.selection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select an object to edit")
                return
            
            # Get model folder from tree
            item = self.objects_tree.item(selected[0])
            model_folder = item['values'][4] if len(item['values']) > 4 else ""
            
            if not model_folder:
                messagebox.showwarning("Invalid Selection", "Cannot edit this object")
                return
            
            dialog = EditObjectDialog(self.root, model_folder)
            self.root.wait_window(dialog)
            
            if dialog.result:
                self._refresh_objects_list()
                self.logger.info(f"Updated object: {dialog.result.get_full_name()}")
                
        except Exception as e:
            self.logger.error(f"Error editing object: {e}")
            messagebox.showerror("Error", f"Failed to edit object: {e}")
    
    def _delete_object(self) -> None:
        """Delete selected object."""
        try:
            selected = self.objects_tree.selection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select an object to delete")
                return
            
            # Get model folder from tree
            item = self.objects_tree.item(selected[0])
            model_folder = item['values'][4] if len(item['values']) > 4 else ""
            object_name = item['values'][0] if len(item['values']) > 0 else "Unknown"
            
            if not model_folder:
                messagebox.showwarning("Invalid Selection", "Cannot delete this object")
                return
            
            dialog = DeleteObjectDialog(self.root, model_folder)
            self.root.wait_window(dialog)
            
            if dialog.result:
                self._refresh_objects_list()
                self.logger.info(f"Deleted object: {object_name}")
                
        except Exception as e:
            self.logger.error(f"Error deleting object: {e}")
            messagebox.showerror("Error", f"Failed to delete object: {e}")
    
    def _refresh_objects_list(self) -> None:
        """Refresh the objects list."""
        try:
            # Clear existing items
            for item in self.objects_tree.get_children():
                self.objects_tree.delete(item)
            
            # Load objects from service
            from vigil.services.object_service import object_service
            objects = object_service.get_all_objects()
            
            # Add objects to tree
            for obj in objects:
                name = obj.get_full_name()
                category = obj.get_category_name()
                phone = obj.phone or "N/A"
                address = obj.get_address()
                model_folder = obj.modelfolder
                
                self.objects_tree.insert('', 'end', values=(name, category, phone, address, model_folder))
            
            self.logger.info(f"Refreshed objects list with {len(objects)} objects")
            
        except Exception as e:
            self.logger.error(f"Error refreshing objects list: {e}")
    
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
        """Open camera and recognition settings dialog."""
        if not authz_manager.can_manage_cameras(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to manage cameras")
            return
        
        # Create settings dialog
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Camera and Recognition Settings")
        settings_window.geometry("500x600")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Camera settings tab
        camera_frame = ttk.Frame(notebook)
        notebook.add(camera_frame, text="Camera")
        
        # Recognition settings tab
        recognition_frame = ttk.Frame(notebook)
        notebook.add(recognition_frame, text="Face Recognition")
        
        # === Camera Settings ===
        ttk.Label(camera_frame, text="Camera Settings", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Camera source
        source_frame = ttk.Frame(camera_frame)
        source_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(source_frame, text="Camera Source:").pack(side='left')
        camera_source_var = tk.StringVar(value=str(video_capture.camera_link or "0"))
        ttk.Entry(source_frame, textvariable=camera_source_var, width=20).pack(side='left', padx=10)
        
        # Resolution
        res_frame = ttk.Frame(camera_frame)
        res_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(res_frame, text="Resolution:").pack(side='left')
        
        # Get resolution setting properly
        stream_setting = settings.get_setting('stream_res_qua', '704,90')
        if ',' in stream_setting:
            resolution_default = stream_setting.split(',')[0]
        else:
            resolution_default = '704'
        
        resolution_var = tk.StringVar(value=resolution_default)
        ttk.Entry(res_frame, textvariable=resolution_var, width=10).pack(side='left', padx=10)
        ttk.Label(res_frame, text="pixels").pack(side='left')
        
        # Quality
        quality_frame = ttk.Frame(camera_frame)
        quality_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(quality_frame, text="Quality:").pack(side='left')
        
        # Get quality setting properly
        stream_setting = settings.get_setting('stream_res_qua', '704,90')
        if ',' in stream_setting:
            quality_default = stream_setting.split(',')[1]
        else:
            quality_default = '90'
        
        quality_var = tk.StringVar(value=quality_default)
        ttk.Entry(quality_frame, textvariable=quality_var, width=10).pack(side='left', padx=10)
        ttk.Label(quality_frame, text="%").pack(side='left')
        
        # === Recognition Settings ===
        ttk.Label(recognition_frame, text="Face Recognition Settings", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Enable recognition
        enabled_frame = ttk.Frame(recognition_frame)
        enabled_frame.pack(fill='x', padx=20, pady=10)
        recognition_enabled_var = tk.BooleanVar(value=settings.get_setting('face_recognition_enabled', '1') == '1')
        ttk.Checkbutton(enabled_frame, text="Enable Face Recognition", variable=recognition_enabled_var).pack(side='left')
        
        # Algorithm
        algo_frame = ttk.Frame(recognition_frame)
        algo_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(algo_frame, text="Detection Algorithm:").pack(side='left')
        algo_var = tk.StringVar(value=settings.get_setting('model_algorithm', 'cnn'))
        algo_combo = ttk.Combobox(algo_frame, textvariable=algo_var, values=['cnn', 'hog'], state='readonly', width=15)
        algo_combo.pack(side='left', padx=10)
        
        # Confidence threshold (actually tolerance for face_recognition library)
        conf_frame = ttk.Frame(recognition_frame)
        conf_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(conf_frame, text="Recognition Tolerance:").pack(side='left')
        conf_var = tk.StringVar(value=settings.get_setting('recognition_confidence_threshold', '0.6'))
        conf_scale = ttk.Scale(conf_frame, from_=0.1, to=1.0, variable=tk.DoubleVar(value=float(conf_var.get())), 
                              orient='horizontal', length=150)
        conf_scale.pack(side='left', padx=10)
        conf_label = ttk.Label(conf_frame, textvariable=conf_var, width=5)
        conf_label.pack(side='left')
        
        def update_conf_label(value):
            conf_var.set(f"{float(value):.2f}")
        conf_scale.config(command=update_conf_label)
        
        # Add explanation label
        ttk.Label(conf_frame, text="(0.1=strict, 0.8=lenient)", font=("Arial", 8)).pack(side='left', padx=5)
        
        # Frame skip
        skip_frame = ttk.Frame(recognition_frame)
        skip_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(skip_frame, text="Process Every N Frames:").pack(side='left')
        skip_var = tk.StringVar(value=settings.get_setting('recognition_frame_skip', '3'))
        ttk.Spinbox(skip_frame, from_=1, to=30, textvariable=skip_var, width=10).pack(side='left', padx=10)
        
        # Cooldown period
        cooldown_frame = ttk.Frame(recognition_frame)
        cooldown_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(cooldown_frame, text="Recognition Cooldown (sec):").pack(side='left')
        cooldown_var = tk.StringVar(value=settings.get_setting('recognition_cooldown', '2'))
        ttk.Spinbox(cooldown_frame, from_=0, to=60, textvariable=cooldown_var, width=10).pack(side='left', padx=10)
        
        # Show unknown faces
        unknown_frame = ttk.Frame(recognition_frame)
        unknown_frame.pack(fill='x', padx=20, pady=5)
        unknown_var = tk.BooleanVar(value=settings.get_setting('show_unknown_faces', '1') == '1')
        ttk.Checkbutton(unknown_frame, text="Show Unknown Face Alerts", variable=unknown_var).pack(side='left')
        
        # Model info
        model_frame = ttk.LabelFrame(recognition_frame, text="Model Information")
        model_frame.pack(fill='x', padx=20, pady=20)
        
        model_info = face_detector.get_model_info()
        info_text = f"Trained: {'Yes' if model_info['is_trained'] else 'No'}\n"
        info_text += f"Known Faces: {model_info['known_faces_count']}\n"
        info_text += f"Algorithm: {model_info['algorithm']}\n"
        info_text += f"Tolerance: {model_info['tolerance']}\n"
        info_text += f"Model Path: {model_info['model_path']}"
        
        ttk.Label(model_frame, text=info_text, justify='left').pack(padx=10, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        def save_settings():
            try:
                # Save camera settings (stream_res_qua needs both resolution and quality)
                current_setting = settings.get_setting('stream_res_qua', '704,90')
                new_setting = f"{resolution_var.get()},{quality_var.get()}"
                
                # Update both values in the database
                settings.set_setting('stream_res_qua', resolution_var.get(), quality_var.get())
                
                # Save recognition settings
                settings.set_setting('face_recognition_enabled', '1' if recognition_enabled_var.get() else '0')
                settings.set_setting('model_algorithm', algo_var.get())
                settings.set_setting('recognition_confidence_threshold', conf_var.get())
                settings.set_setting('recognition_frame_skip', skip_var.get())
                settings.set_setting('recognition_cooldown', cooldown_var.get())
                settings.set_setting('show_unknown_faces', '1' if unknown_var.get() else '0')
                
                # Update face detector settings
                face_detector.set_algorithm(algo_var.get())
                face_detector.set_tolerance(float(conf_var.get()))
                
                # Update runtime settings
                self.recognition_enabled = recognition_enabled_var.get()
                self.recognition_enabled_var.set(self.recognition_enabled)
                
                messagebox.showinfo("Success", "Settings saved successfully!")
                settings_window.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {e}")
        
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side='right', padx=5)
        
        # Center dialog
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (settings_window.winfo_width() // 2)
        y = (settings_window.winfo_screenheight() // 2) - (settings_window.winfo_height() // 2)
        settings_window.geometry(f"+{x}+{y}")
    
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
                self.frame_count = 0
                self.last_recognition_frame = 0
                self.recognition_stats = {'total_faces': 0, 'recognized_faces': 0, 'unknown_faces': 0}
                self.last_recognition_time = {}
                
                # Load recognition settings
                self.recognition_enabled = settings.get_setting('face_recognition_enabled', '1') == '1'
                self.recognition_enabled_var.set(self.recognition_enabled)
                
                self.status_label.config(text="Camera started")
                
                if self.recognition_enabled and face_detector.is_trained():
                    self.recognition_label.config(text="Recognition: Active")
                elif self.recognition_enabled:
                    self.recognition_label.config(text="Recognition: No Model")
                else:
                    self.recognition_label.config(text="Recognition: Disabled")
                
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
            self.face_count_label.config(text="Faces: 0")
            self.recognized_faces_label.config(text="Recognized: None")
            self.recognition_stats_label.config(text="Accuracy: 0%")
            
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
    
    def _toggle_recognition(self) -> None:
        """Toggle face recognition on/off."""
        self.recognition_enabled = self.recognition_enabled_var.get()
        
        if self.is_camera_running:
            if self.recognition_enabled:
                self.recognition_label.config(text="Recognition: Active")
                event_logger.log_system_event('recognition_enabled', 'Face recognition enabled')
            else:
                self.recognition_label.config(text="Recognition: Disabled")
                event_logger.log_system_event('recognition_disabled', 'Face recognition disabled')
        
        self.logger.info(f"Face recognition {'enabled' if self.recognition_enabled else 'disabled'}")
    
    def _process_frame(self, frame) -> None:
        """Process video frame for display and recognition."""
        try:
            self.current_frame = frame.copy()
            self.frame_count += 1
            
            # Get recognition settings
            frame_skip = int(settings.get_setting('recognition_frame_skip', '3'))
            confidence_threshold = float(settings.get_setting('recognition_confidence_threshold', '0.7'))
            cooldown_period = int(settings.get_setting('recognition_cooldown', '2'))
            
            # Initialize variables for this frame
            recognized_faces = []
            current_time = time.time()
            
            # Perform face recognition if enabled and trained
            if (self.recognition_enabled and 
                face_detector.is_trained() and 
                (self.frame_count - self.last_recognition_frame) >= frame_skip):
                
                self.last_recognition_frame = self.frame_count
                
                # Recognize faces with confidence threshold
                # Use the tolerance directly from settings, not inverted confidence
                tolerance = float(confidence_threshold) if confidence_threshold > 0.5 else 0.6
                recognized_faces = face_detector.recognize_faces(frame, tolerance=tolerance)
                
                # Filter faces based on confidence and cooldown
                filtered_faces = []
                for face in recognized_faces:
                    face_name = face['name']
                    confidence = face['confidence']
                    
                    # Check cooldown period for recognized faces
                    if face_name != 'Unknown':
                        last_time = self.last_recognition_time.get(face_name, 0)
                        if current_time - last_time >= cooldown_period:
                            filtered_faces.append(face)
                            self.last_recognition_time[face_name] = current_time
                            
                            # Log recognition event
                            event_logger.log_face_recognition(
                                face_name, 
                                confidence,
                                camera_source=str(video_capture.current_source)
                            )
                    else:
                        # Always log unknown faces (or implement separate cooldown)
                        filtered_faces.append(face)
                        event_logger.log_unknown_face(
                            confidence,
                            camera_source=str(video_capture.current_source)
                        )
                
                recognized_faces = filtered_faces
                
                # Update statistics
                self._update_recognition_stats(recognized_faces)
                
                # Draw face boxes on frame
                frame = face_detector.draw_face_boxes(frame, recognized_faces)
            
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
            
            # Update displays
            self._update_status_displays(recognized_faces)
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
    
    def _update_recognition_stats(self, recognized_faces: list) -> None:
        """Update recognition statistics."""
        self.recognition_stats['total_faces'] += len(recognized_faces)
        
        for face in recognized_faces:
            if face['name'] != 'Unknown':
                self.recognition_stats['recognized_faces'] += 1
            else:
                self.recognition_stats['unknown_faces'] += 1
    
    def _update_status_displays(self, recognized_faces: list) -> None:
        """Update status displays with current information."""
        try:
            # Update FPS
            fps = video_capture.get_fps()
            self.fps_label.config(text=f"FPS: {fps:.1f}")
            
            # Update face count
            face_count = len(recognized_faces)
            self.face_count_label.config(text=f"Faces: {face_count}")
            
            # Update recognized faces list
            if recognized_faces:
                recognized_names = [face['name'] for face in recognized_faces if face['name'] != 'Unknown']
                if recognized_names:
                    unique_names = list(set(recognized_names))
                    self.recognized_faces_label.config(text=f"Recognized: {', '.join(unique_names[:3])}")
                else:
                    self.recognized_faces_label.config(text="Recognized: Unknown faces only")
            else:
                self.recognized_faces_label.config(text="Recognized: None")
            
            # Update accuracy
            total = self.recognition_stats['total_faces']
            if total > 0:
                accuracy = (self.recognition_stats['recognized_faces'] / total) * 100
                self.recognition_stats_label.config(text=f"Accuracy: {accuracy:.1f}%")
            
        except Exception as e:
            self.logger.error(f"Error updating status displays: {e}")
    
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

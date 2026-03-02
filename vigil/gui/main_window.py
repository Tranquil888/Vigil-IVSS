"""
Main application window for Vigil surveillance system.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import time
import os
from time import strftime
from typing import Optional
from vigil.gui.dialogs.auth_dialog import AuthenticationDialog
from vigil.gui.dialogs.training_dialog import TrainingDialog
from vigil.auth.authorization import authz_manager
from vigil.utils.logging_config import get_ui_logger
from vigil.video.capture import video_capture
from vigil.video.processing import frame_processor
from vigil.recognition.face_detector import face_detector
from vigil.gui.dialogs.object_dialogs import AddObjectDialog, EditObjectDialog, DeleteObjectDialog
from vigil.gui.dialogs.event_journal_dialog import EventJournalDialog
from vigil.recognition.training_service import training_service
from vigil.events.logger import event_logger
from vigil.events.session_manager import session_manager
from vigil.config.settings import settings
from vigil.database.manager import get_events_db, get_objects_db


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
        self._last_filtered_faces = []  # Store last filtered results for stable display
        self._last_recognition_update = 0  # Throttle recognition display updates
        self._current_frame_photo = None
        self._last_frame_time = None  # Initialize FPS tracking
        
        # Avatar rectangles for recent recognitions
        self.recent_avatars = []  # Circular buffer for recent avatar data
        self.avatar_labels = []   # List of avatar label widgets
        self.max_recent_avatars = 5
        self.avatar_index = 0     # Current index for circular buffer
        
        self._setup_window()
        self._create_widgets()
        
        # Show authentication dialog on startup
        self.root.after(100, self._authenticate_user)
    
    def _setup_window(self) -> None:
        """Setup the main window properties."""
        self.root.title("Vigil - Intelligent Video Surveillance System")
        self.root.geometry("1400x900")
        self.root.minsize(800, 600)
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self) -> None:
        """Create main window widgets."""
        # Create menu bar
        self._create_menu_bar()
        
        # Create main toolbar
        self._create_toolbar()
        
        # Create filter controls
        self._create_filter_controls()
        
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
        events_menu.add_command(label="Event Images", command=self._view_photo_journal)
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
    
    def _create_filter_controls(self) -> None:
        """Create object filtering controls."""
        from vigil.config.constants import OBJECT_TYPES
        
        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(side='top', fill='x', padx=5, pady=2)
        
        # Object name filter
        ttk.Label(filter_frame, text="Object Name:").pack(side='left', padx=(0, 5))
        self.object_name_var = tk.StringVar()
        self.object_name_entry = ttk.Entry(filter_frame, textvariable=self.object_name_var, width=20)
        self.object_name_entry.pack(side='left', padx=(0, 10))
        
        # Object type filter
        ttk.Label(filter_frame, text="Object Type:").pack(side='left', padx=(0, 5))
        self.object_type_var = tk.StringVar()
        self.object_type_combo = ttk.Combobox(filter_frame, textvariable=self.object_type_var, 
                                            values=["All"] + OBJECT_TYPES, width=15, state='readonly')
        self.object_type_combo.set("All")
        self.object_type_combo.pack(side='left', padx=(0, 10))
        
        # Filter buttons
        ttk.Button(filter_frame, text="Apply Filters", command=self._apply_object_filters).pack(side='left', padx=(0, 5))
        ttk.Button(filter_frame, text="Clear Filters", command=self._clear_object_filters).pack(side='left', padx=(0, 10))
        
        # Filter status
        self.filter_status_label = ttk.Label(filter_frame, text="Showing all objects", font=("Arial", 9))
        self.filter_status_label.pack(side='left', padx=(10, 0))
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side='bottom', fill='x')
        
        self.status_label = ttk.Label(self.status_bar, text="Ready", relief='sunken')
        self.status_label.pack(side='left', fill='x', expand=True, padx=2, pady=2)
        
        # Time label
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
        """Create the camera monitoring tab with new layout."""
        # Main horizontal container
        main_container = ttk.Frame(self.camera_frame)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        main_container.columnconfigure(0, weight=2)  # Objects log (40%)
        main_container.columnconfigure(1, weight=3)  # Video feed (60%)
        main_container.rowconfigure(0, weight=1)
        
        # Left side: Recognized Objects Log
        self._create_objects_log(main_container)
        
        # Right side: Video Feed
        self._create_video_feed(main_container)
        
        # Bottom: Recognition controls
        self._create_recognition_controls()
    
    def _create_objects_log(self, parent) -> None:
        """Create the recognized objects log on the left side."""
        objects_frame = ttk.LabelFrame(parent, text="Recognized Objects Log")
        objects_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        objects_frame.columnconfigure(0, weight=1)
        objects_frame.rowconfigure(0, weight=1)
        
        # Create treeview for objects
        object_columns = ('timestamp', 'object_name', 'object_type', 'confidence', 'event_id')
        self.recognized_objects_tree = ttk.Treeview(objects_frame, columns=object_columns, show='headings')
        
        # Define headings
        self.recognized_objects_tree.heading('timestamp', text='Time')
        self.recognized_objects_tree.heading('object_name', text='Object Name')
        self.recognized_objects_tree.heading('object_type', text='Type')
        self.recognized_objects_tree.heading('confidence', text='Confidence')
        self.recognized_objects_tree.heading('event_id', text='Event ID')
        
        # Configure column widths
        self.recognized_objects_tree.column('timestamp', width=120)
        self.recognized_objects_tree.column('object_name', width=120)
        self.recognized_objects_tree.column('object_type', width=80)
        self.recognized_objects_tree.column('confidence', width=80)
        self.recognized_objects_tree.column('event_id', width=80)
        
        # Scrollbar for objects
        objects_scrollbar = ttk.Scrollbar(objects_frame, orient=tk.VERTICAL, command=self.recognized_objects_tree.yview)
        self.recognized_objects_tree.configure(yscrollcommand=objects_scrollbar.set)
        
        # Grid widgets
        self.recognized_objects_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        objects_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Initialize objects data
        self._refresh_objects_log()
        
        # Start auto-refresh schedule
        self.root.after(5000, self._schedule_objects_refresh)
    
    def _create_video_feed(self, parent) -> None:
        """Create the video feed on the right side."""
        video_frame = ttk.LabelFrame(parent, text="Video Feed")
        video_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        # Create canvas for video display
        self.video_canvas = tk.Canvas(
            video_frame,
            background='black',
            highlightthickness=0
        )
        self.video_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
    
    def _create_recognition_controls(self) -> None:
        """Create recognition controls at the bottom."""
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
        # Main container for events tab
        main_container = ttk.Frame(self.events_frame)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Top section - Event log and avatars side by side
        top_section = ttk.Frame(main_container)
        top_section.pack(fill='both', expand=True)
        
        # Left side - Event log (70% width)
        events_frame = ttk.LabelFrame(top_section, text="Event Log")
        events_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Create treeview for events (reduced height)
        columns = ("Time", "Event", "Object", "Confidence")
        self.events_tree = ttk.Treeview(events_frame, columns=columns, show='headings', height=12)
        
        for col in columns:
            self.events_tree.heading(col, text=col)
            self.events_tree.column(col, width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(events_frame, orient='vertical', command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=scrollbar.set)
        
        self.events_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Right side - Recent Avatars (30% width, fixed size)
        avatars_frame = ttk.LabelFrame(top_section, text="Recent Recognitions")
        avatars_frame.pack(side='right', fill='y', padx=(5, 0))
        
        # Create a scrollable frame for avatars with fixed width
        avatar_canvas = tk.Canvas(avatars_frame, height=300, width=150)
        avatar_scrollbar = ttk.Scrollbar(avatars_frame, orient="vertical", command=avatar_canvas.yview)
        avatar_scrollable_frame = ttk.Frame(avatar_canvas)
        
        avatar_canvas.configure(yscrollcommand=avatar_scrollbar.set)
        avatar_canvas_frame = avatar_canvas.create_window((0, 0), window=avatar_scrollable_frame, anchor="nw", width=150)
        
        avatar_scrollable_frame.bind(
            "<Configure>",
            lambda e: avatar_canvas.configure(scrollregion=avatar_canvas.bbox("all"))
        )
        
        self._create_avatar_rectangles(avatar_scrollable_frame)
        
        avatar_canvas.pack(side="left", fill="both", expand=False)
        avatar_scrollbar.pack(side="right", fill="y")
        
        # Bottom section - Events controls (always visible)
        events_controls = ttk.Frame(main_container)
        events_controls.pack(side='bottom', fill='x', pady=(5, 0), anchor='w')
        
        ttk.Button(events_controls, text="View Events", command=self._view_events).pack(side='left', padx=2)
        ttk.Button(events_controls, text="Event Images", command=self._view_photo_journal).pack(side='left', padx=2)
        ttk.Button(events_controls, text="Refresh", command=self._refresh_events).pack(side='left', padx=2)
        ttk.Button(events_controls, text="Export", command=self._export_events).pack(side='left', padx=2)
        ttk.Button(events_controls, text="Clear", command=self._clear_events).pack(side='left', padx=2)
    
    def _create_avatar_rectangles(self, parent_frame) -> None:
        """Create 5 avatar rectangles for recent recognitions."""
        # Initialize recent avatars buffer
        self.recent_avatars = [{'name': '', 'avatar_path': None} for _ in range(self.max_recent_avatars)]
        self.avatar_labels = []
        
        # VIGIL letters for initial display
        vigil_letters = ['V', 'I', 'G', 'I', 'L']
        
        for i in range(self.max_recent_avatars):
            # Create frame for each avatar rectangle
            avatar_frame = ttk.Frame(parent_frame, relief="solid", borderwidth=1)
            avatar_frame.pack(fill='x', pady=1)
            
            # Avatar label (remove size constraints for images)
            avatar_label = tk.Label(avatar_frame, text=vigil_letters[i], 
                                  bg="lightgray", fg="darkblue", 
                                  font=("Arial", 20, "bold"))
            avatar_label.pack(pady=2)
            
            # Name label (smaller font)
            name_label = ttk.Label(avatar_frame, text="", font=("Arial", 7))
            name_label.pack(pady=(0, 2))
            
            # Store references
            self.avatar_labels.append({
                'frame': avatar_frame,
                'avatar_label': avatar_label,
                'name_label': name_label
            })
    
    def _update_recent_avatar(self, object_name: str) -> None:
        """Update the recent avatars display with a new recognition."""
        try:
            # Get avatar path for the object
            avatar_path = self._get_avatar_path_for_object(object_name)
            
            # Update circular buffer
            self.recent_avatars[self.avatar_index] = {
                'name': object_name,
                'avatar_path': avatar_path
            }
            
            # Update UI display
            self._refresh_avatar_display()
            
            # Move to next position (circular buffer)
            self.avatar_index = (self.avatar_index + 1) % self.max_recent_avatars
            
        except Exception as e:
            self.logger.error(f"Error updating recent avatar: {e}")
    
    def _get_avatar_path_for_object(self, object_name: str) -> str:
        """Get avatar path for an object name."""
        try:
            # Force a fresh database connection to avoid caching issues
            objects_db = get_objects_db()
            
            # Debug: Log database path (make it absolute)
            abs_db_path = os.path.abspath(objects_db.db_path)
            self.logger.info(f"Database path: {abs_db_path}")
            
            # Debug: Log what we're searching for
            self.logger.info(f"Searching for avatar for: {object_name}")
            
            # Force fresh connection by creating new instance
            from vigil.database.manager import ObjectsDatabase
            fresh_db = ObjectsDatabase()
            
            # Get all objects from the correct table (People table, not objects table)
            all_objects = fresh_db.get_all_objects()
            self.logger.info(f"Found {len(all_objects)} objects in database")
            
            # If get_all_objects() returns empty, try direct SQL to People table
            if len(all_objects) == 0:
                self.logger.warning("No objects found via get_all_objects - trying direct SQL to People table...")
                import sqlite3
                conn = sqlite3.connect(fresh_db.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM People")
                count = cursor.fetchone()[0]
                self.logger.info(f"Direct SQL found {count} objects in People table")
                if count > 0:
                    cursor.execute("SELECT first_name, last_name, foto FROM People")
                    rows = cursor.fetchall()
                    all_objects = []
                    for row in rows:
                        all_objects.append({
                            'first_name': row[0],
                            'last_name': row[1], 
                            'foto': row[2]
                        })
                    self.logger.info(f"Loaded {len(all_objects)} objects from People table")
                conn.close()
            
            for db_obj in all_objects:
                # Create full name from first_name and last_name
                first_name = db_obj.get('first_name', '')
                last_name = db_obj.get('last_name', '')
                full_name = f"{last_name} {first_name}".strip()
                modelfolder = db_obj.get('modelfolder', '')
                foto = db_obj.get('foto', '')
                
                # Debug: Log each object
                self.logger.info(f"DB Object: full_name='{full_name}', first_name='{first_name}', last_name='{last_name}', modelfolder='{modelfolder}', foto='{foto}'")
                
                # Check if object_name contains the database object's name parts
                if full_name and full_name in object_name:
                    obj = db_obj
                    self.logger.info(f"Found object by full name: {full_name}, avatar: {obj.get('foto')}")
                    break
                # Also check individual name parts
                if first_name and first_name in object_name:
                    obj = db_obj
                    self.logger.info(f"Found object by first name: {first_name}, avatar: {obj.get('foto')}")
                    break
                if last_name and last_name in object_name:
                    obj = db_obj
                    self.logger.info(f"Found object by last name: {last_name}, avatar: {obj.get('foto')}")
                    break
                # Check modelfolder as well
                if modelfolder and modelfolder in object_name:
                    obj = db_obj
                    self.logger.info(f"Found object by modelfolder: {modelfolder}, avatar: {obj.get('foto')}")
                    break
            
            if obj and obj.get('foto'):
                # Construct full path
                avatar_path = os.path.join(os.getcwd(), "data", "photo", "objects", obj['foto'])
                self.logger.info(f"Constructed avatar path: {avatar_path}")
                if os.path.exists(avatar_path):
                    return avatar_path
                else:
                    self.logger.warning(f"Avatar file does not exist: {avatar_path}")
            
            # Get object type using the working method and return category-specific default avatar
            object_type = self._get_object_type_for_name(object_name)
            default_avatar = self._get_default_avatar_by_type(object_type)
            default_path = os.path.join(os.getcwd(), "data", "photo", "objects", default_avatar)
            self.logger.info(f"Using default avatar for {object_type}: {default_path}")
            return default_path
            
        except Exception as e:
            self.logger.error(f"Error getting avatar path for {object_name}: {e}")
            return os.path.join(os.getcwd(), "data", "photo", "objects", "no_avatar_red.jpg")
    
    def _get_default_avatar_by_type(self, object_type: str) -> str:
        """Get default avatar filename based on object type."""
        if object_type == 'Resident' or object_type == '1':
            return 'no_avatar_green.jpg'
        elif object_type == 'Visitor' or object_type == '3':
            return 'no_avatar_blue.jpg'
        elif object_type == 'Staff' or object_type == '2':
            return 'no_avatar_grey.jpg'
        else:  # Unknown or any other
            return 'no_avatar_red.jpg'
    
    def _refresh_avatar_display(self) -> None:
        """Refresh the avatar display with current buffer data."""
        try:
            for i, avatar_data in enumerate(self.recent_avatars):
                if i < len(self.avatar_labels):
                    label_set = self.avatar_labels[i]
                    
                    if avatar_data.get('name') and avatar_data.get('avatar_path'):
                        # Load and display avatar
                        try:
                            avatar_path = avatar_data['avatar_path']
                            self.logger.info(f"Loading avatar: {avatar_path}")
                            
                            if os.path.exists(avatar_path):
                                image = Image.open(avatar_path)
                                image = image.resize((120, 120), Image.Resampling.LANCZOS)
                                photo = ImageTk.PhotoImage(image)
                                
                                # Clear previous image reference
                                label_set['avatar_label'].image = None
                                
                                label_set['avatar_label'].configure(image=photo, text="", bg="white")
                                label_set['avatar_label'].image = photo  # Keep reference
                                label_set['name_label'].configure(text=avatar_data['name'][:15])  # Truncate long names
                                
                                self.logger.info(f"Successfully loaded avatar for {avatar_data['name']}")
                            else:
                                # Show default if file doesn't exist
                                self.logger.warning(f"Avatar file not found: {avatar_path}")
                                label_set['avatar_label'].configure(image="", text="DEF", bg="lightgray")
                                label_set['name_label'].configure(text=avatar_data['name'][:15])
                            
                        except Exception as e:
                            # Fallback to text if image fails
                            self.logger.error(f"Error loading avatar image: {e}")
                            label_set['avatar_label'].configure(image="", text="ERR", bg="red")
                            label_set['name_label'].configure(text=avatar_data['name'][:15])
                    else:
                        # Empty slot - show VIGIL letter
                        vigil_letters = ['V', 'I', 'G', 'I', 'L']
                        label_set['avatar_label'].configure(image="", text=vigil_letters[i])
                        label_set['name_label'].configure(text="")
                        
        except Exception as e:
            self.logger.error(f"Error refreshing avatar display: {e}")
    
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
        can_create_users = authz_manager.can_manage_users(self.current_role)
        can_view_users = authz_manager.can_view_user_list(self.current_role)
        
        self.users_menu.entryconfig("Create User", state='normal' if can_create_users else 'disabled')
        self.users_menu.entryconfig("User List", state='normal' if can_view_users else 'disabled')
    
    def _on_closing(self) -> None:
        """Handle window closing event."""
        if messagebox.askokcancel("Quit", "Do you want to quit Vigil?"):
            self.logger.info("Application closing")
            
            # Stop camera if running
            if self.is_camera_running:
                video_capture.stop_capture()
                self.is_camera_running = False
            
            # Shutdown session manager
            try:
                session_manager.shutdown()
                self.logger.info("Session manager shutdown complete")
            except Exception as e:
                self.logger.error(f"Error shutting down session manager: {e}")
            
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
        if not authz_manager.can_view_user_list(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to view user list")
            return
        
        from vigil.gui.dialogs.user_list_dialog import UserListDialog
        dialog = UserListDialog(self.root, self.current_role)
        dialog.show()
    
    def _add_object(self) -> None:
        """Add a new object."""
        try:
            dialog = AddObjectDialog(self.root, self.current_role)
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
            
            dialog = EditObjectDialog(self.root, model_folder, self.current_role)
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
        
        # Load existing camera settings from database
        from vigil.database.manager import get_camera_db
        camera_db = get_camera_db()
        existing_camera = camera_db.get_camera('channel_01')
        
        # Determine source type and path from database
        if existing_camera:
            source_type = existing_camera.get('source_type', 'camera')
            camera_link = existing_camera.get('link', '0')
            camera_name = existing_camera.get('name', '')
        else:
            source_type = 'camera'
            camera_link = str(video_capture.camera_link or "0")
            camera_name = ''
        
        # Source type selection
        source_type_frame = ttk.Frame(camera_frame)
        source_type_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(source_type_frame, text="Source Type:").pack(side='left')
        
        source_type_var = tk.StringVar(value=source_type)
        camera_radio = ttk.Radiobutton(source_type_frame, text="Camera", variable=source_type_var, value='camera', 
                                      command=lambda: self._update_source_ui(source_type_var.get(), camera_link_frame, video_file_frame))
        camera_radio.pack(side='left', padx=10)
        
        file_radio = ttk.Radiobutton(source_type_frame, text="Video File", variable=source_type_var, value='file',
                                    command=lambda: self._update_source_ui(source_type_var.get(), camera_link_frame, video_file_frame))
        file_radio.pack(side='left', padx=10)
        
        # Camera source frame
        camera_link_frame = ttk.LabelFrame(camera_frame, text="Camera Settings")
        camera_link_frame.pack(fill='x', padx=20, pady=10)
        
        camera_source_frame = ttk.Frame(camera_link_frame)
        camera_source_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(camera_source_frame, text="Camera Link:").pack(side='left')
        camera_source_var = tk.StringVar(value=camera_link if source_type == 'camera' else '0')
        camera_source_entry = ttk.Entry(camera_source_frame, textvariable=camera_source_var, width=30)
        camera_source_entry.pack(side='left', padx=10, fill='x', expand=True)
        
        # Video file frame
        video_file_frame = ttk.LabelFrame(camera_frame, text="Video File Settings")
        video_file_frame.pack(fill='x', padx=20, pady=10)
        
        video_file_path_frame = ttk.Frame(video_file_frame)
        video_file_path_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(video_file_path_frame, text="Video File:").pack(side='left')
        video_file_var = tk.StringVar(value=camera_link if source_type == 'file' else '')
        video_file_entry = ttk.Entry(video_file_path_frame, textvariable=video_file_var, width=25)
        video_file_entry.pack(side='left', padx=10, fill='x', expand=True)
        
        def browse_video_file():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Select Video File",
                filetypes=[
                    ("Video Files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"),
                    ("MP4 Files", "*.mp4"),
                    ("AVI Files", "*.avi"),
                    ("MOV Files", "*.mov"),
                    ("MKV Files", "*.mkv"),
                    ("All Files", "*.*")
                ]
            )
            if file_path:
                video_file_var.set(file_path)
        
        ttk.Button(video_file_path_frame, text="Browse", command=browse_video_file).pack(side='right', padx=5)
        
        # Video playback options
        playback_frame = ttk.Frame(video_file_frame)
        playback_frame.pack(fill='x', padx=10, pady=5)
        
        loop_var = tk.BooleanVar(value=settings.get_setting('video_loop_playback', '0') == '1')
        ttk.Checkbutton(playback_frame, text="Loop Playback", variable=loop_var).pack(side='left', padx=5)
        
        show_progress_var = tk.BooleanVar(value=settings.get_setting('video_progress_show', '1') == '1')
        ttk.Checkbutton(playback_frame, text="Show Progress", variable=show_progress_var).pack(side='left', padx=5)
        
        # Video speed control
        speed_frame = ttk.Frame(video_file_frame)
        speed_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(speed_frame, text="Playback Speed:").pack(side='left')
        
        speed_var = tk.StringVar(value=settings.get_setting('video_playback_speed', '1.0'))
        speed_combo = ttk.Combobox(speed_frame, textvariable=speed_var, width=10, state='readonly')
        speed_combo['values'] = ('0.25', '0.5', '0.75', '1.0', '1.25', '1.5', '2.0')
        speed_combo.pack(side='left', padx=10)
        # Don't override the loaded setting - let it use the value from settings.get_setting()
        
        # Initially hide/show frames based on source type
        if source_type == 'file':
            camera_link_frame.pack_forget()
        else:
            video_file_frame.pack_forget()
        
        # Store reference for UI updates
        settings_window.camera_source_var = camera_source_var
        settings_window.video_file_var = video_file_var
        settings_window.source_type_var = source_type_var
        settings_window.loop_var = loop_var
        settings_window.show_progress_var = show_progress_var
        settings_window.speed_var = speed_var
        
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
        
        # FPS
        fps_frame = ttk.Frame(camera_frame)
        fps_frame.pack(fill='x', padx=20, pady=5)
        ttk.Label(fps_frame, text="Max FPS:").pack(side='left')
        
        fps_default = settings.get_setting('camera_max_fps', '30')
        fps_var = tk.StringVar(value=fps_default)
        fps_combo = ttk.Combobox(fps_frame, textvariable=fps_var, width=10, values=['15', '30', '60', '120'], state='readonly')
        fps_combo.pack(side='left', padx=10)
        ttk.Label(fps_frame, text="fps").pack(side='left')
        
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
                # Get source type and corresponding settings
                source_type = source_type_var.get()
                
                if source_type == 'camera':
                    # Save camera settings to camera database
                    camera_link = camera_source_var.get()
                    camera_name = f"Camera {camera_link}"
                    
                    # Update or create camera record
                    from vigil.database.manager import get_camera_db
                    camera_db = get_camera_db()
                    
                    # Check if camera already exists
                    existing_camera = camera_db.get_camera('channel_01')
                    if existing_camera:
                        camera_db.update_camera('channel_01', 
                                              link=camera_link, 
                                              source_type='camera',
                                              name=camera_name)
                    else:
                        camera_db.create_camera('channel_01', 
                                              link=camera_link, 
                                              source_type='camera',
                                              name=camera_name)
                    
                    # Update video_capture camera_link reference
                    video_capture.camera_link = camera_link
                    
                else:  # file
                    # Save video file settings to camera database
                    video_file = video_file_var.get()
                    if not video_file:
                        messagebox.showerror("Error", "Please select a video file")
                        return
                    
                    video_name = os.path.basename(video_file)
                    
                    # Update or create camera record for video file
                    from vigil.database.manager import get_camera_db
                    camera_db = get_camera_db()
                    
                    # Check if video source already exists
                    existing_camera = camera_db.get_camera('channel_01')
                    if existing_camera:
                        camera_db.update_camera('channel_01', 
                                              link=video_file, 
                                              source_type='file',
                                              name=video_name)
                    else:
                        camera_db.create_camera('channel_01', 
                                              link=video_file, 
                                              source_type='file',
                                              name=video_name)
                    
                    # Update video_capture camera_link reference
                    video_capture.camera_link = video_file
                
                # Save video playback settings
                settings.set_setting('video_loop_playback', '1' if loop_var.get() else '0')
                settings.set_setting('video_progress_show', '1' if show_progress_var.get() else '0')
                settings.set_setting('video_playback_speed', speed_var.get())
                
                # Save camera settings (stream_res_qua needs both resolution and quality)
                current_setting = settings.get_setting('stream_res_qua', '704,90')
                new_setting = f"{resolution_var.get()},{quality_var.get()}"
                
                # Update both values in the database
                settings.set_setting('stream_res_qua', resolution_var.get(), quality_var.get())
                
                # Save FPS setting
                settings.set_setting('camera_max_fps', fps_var.get())
                
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
    
    def _update_source_ui(self, source_type: str, camera_frame: ttk.Widget, video_frame: ttk.Widget) -> None:
        """Update UI based on source type selection."""
        if source_type == 'camera':
            camera_frame.pack(fill='x', padx=20, pady=10, after=video_frame)
            video_frame.pack_forget()
        else:  # file
            video_frame.pack(fill='x', padx=20, pady=10, after=camera_frame)
            camera_frame.pack_forget()
    
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
        
        try:
            EventJournalDialog(self.root, self)
        except Exception as e:
            self.logger.error(f"Error opening event journal: {e}")
            messagebox.showerror("Error", f"Failed to open event journal: {e}")
    
    def _view_photo_journal(self) -> None:
        """Open photo journal dialog."""
        if not authz_manager.can_view_events(self.current_role):
            messagebox.showerror("Access Denied", "You don't have permission to view events")
            return
        
        try:
            from vigil.gui.dialogs.photo_journal_dialog import PhotoJournalDialog
            PhotoJournalDialog(self.root, self).show()
        except Exception as e:
            self.logger.error(f"Error opening photo journal: {e}")
            messagebox.showerror("Error", f"Failed to open photo journal: {e}")
    
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
            
            # Check if source is a video file
            is_video_file = (isinstance(camera_source, str) and 
                           camera_source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv')))
            
            # Open video source
            if video_capture.open_source(camera_source):
                # Start frame capture
                video_capture.start_capture(self._process_frame)
                
                self.is_camera_running = True
                self.frame_count = 0
                self.last_recognition_frame = 0
                self.recognition_stats = {'total_faces': 0, 'recognized_faces': 0, 'unknown_faces': 0}
                self.last_recognition_time = {}
                self._last_filtered_faces = []  # Store last filtered results for stable display
                self._last_recognition_update = 0  # Throttle recognition display updates
                self._last_frame_time = float(time.time())  # Initialize FPS tracking with actual time value
                
                # Video progress tracking
                self.progress_update_timer = None
                self.video_progress_bar = None
                
                # Load recognition settings
                self.recognition_enabled = settings.get_setting('face_recognition_enabled', '1') == '1'
                self.recognition_enabled_var.set(self.recognition_enabled)
                
                # Set appropriate status message
                if is_video_file:
                    video_name = os.path.basename(camera_source)
                    self.status_label.config(text=f"Playing video: {video_name}")
                    source_desc = f"Video file: {video_name}"
                else:
                    self.status_label.config(text="Camera started")
                    source_desc = f"Camera: {camera_source}"
                
                if self.recognition_enabled and face_detector.is_trained():
                    self.recognition_label.config(text="Recognition: Active")
                elif self.recognition_enabled:
                    self.recognition_label.config(text="Recognition: No Model")
                else:
                    self.recognition_label.config(text="Recognition: Disabled")
                
                # Update button states
                self.start_camera_btn.config(state='disabled')
                self.stop_camera_btn.config(state='normal')
                
                # Start video progress updates if it's a video file and progress display is enabled
                if is_video_file and settings.get_setting('video_progress_show', '1') == '1':
                    self._start_video_progress_updates()
                
                # Log system event
                event_logger.log_system_event('camera_started', f'Video source started: {source_desc}')
                
                self.logger.info(f"Video source started: {source_desc}")
            else:
                messagebox.showerror("Error", "Failed to start video source")
                
        except Exception as e:
            self.logger.error(f"Error starting video source: {e}")
            messagebox.showerror("Error", f"Failed to start video source: {e}")
    
    def _stop_camera(self) -> None:
        """Stop camera capture."""
        try:
            # Stop video progress updates
            self._stop_video_progress_updates()
            
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
    
    def _start_video_progress_updates(self) -> None:
        """Start video progress bar updates."""
        if not video_capture.is_video_file_source():
            return
        
        # Create progress bar in camera controls area if it doesn't exist
        if not self.video_progress_bar:
            progress_frame = ttk.Frame(self.camera_frame)
            progress_frame.pack(fill='x', padx=5, pady=2, before=self.camera_frame.winfo_children()[1])
            
            ttk.Label(progress_frame, text="Progress:").pack(side='left', padx=5)
            self.video_progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
            self.video_progress_bar.pack(side='left', fill='x', expand=True, padx=5)
            
            self.progress_label = ttk.Label(progress_frame, text="0:00 / 0:00")
            self.progress_label.pack(side='right', padx=5)
        
        # Start progress updates
        self._update_video_progress()
    
    def _update_video_progress(self) -> None:
        """Update video progress display."""
        if not self.is_camera_running or not video_capture.is_video_file_source():
            return
        
        progress_info = video_capture.get_video_progress()
        
        if progress_info['is_video_file']:
            # Update progress bar
            self.video_progress_bar['value'] = progress_info['progress_percent']
            
            # Format time display
            current_time = self._format_time(progress_info['current_frame'], video_capture.get_fps())
            total_time = self._format_time(progress_info['total_frames'], video_capture.get_fps())
            self.progress_label.config(text=f"{current_time} / {total_time}")
            
            # Check if video is complete
            if progress_info['progress_percent'] >= 99.9:
                self._on_video_complete()
                return
        
        # Schedule next update
        self.progress_update_timer = self.root.after(500, self._update_video_progress)
    
    def _format_time(self, frames: int, fps: float) -> str:
        """Format frame count as MM:SS time string."""
        if fps <= 0:
            return "0:00"
        
        seconds = int(frames / fps)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def _on_video_complete(self) -> None:
        """Handle video completion."""
        if not video_capture.is_video_file_source():
            return
        
        # Check if loop playback is enabled
        if settings.get_setting('video_loop_playback', '0') == '1':
            self.logger.info("Video completed, looping...")
            # Video will automatically loop in VideoCapture class
        else:
            self.logger.info("Video completed")
            self.status_label.config(text="Video completed")
            
            # Show completion dialog
            if messagebox.askyesno("Video Complete", "Video has finished playing. Would you like to replay?"):
                # Restart video
                if video_capture.is_video_file_source():
                    video_capture.seek_to_frame(0)
                    self.status_label.config(text="Replaying video...")
            else:
                # Stop camera
                self._stop_camera()
    
    def _stop_video_progress_updates(self) -> None:
        """Stop video progress updates."""
        if self.progress_update_timer:
            self.root.after_cancel(self.progress_update_timer)
            self.progress_update_timer = None
        
        # Hide progress bar
        if self.video_progress_bar:
            progress_frame = self.video_progress_bar.master
            progress_frame.pack_forget()
            self.video_progress_bar = None
    
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
            
            # Feed frame to video buffer continuously
            session_manager.feed_frame_to_buffer(frame)
            
            # Get recognition settings
            frame_skip = int(settings.get_setting('recognition_frame_skip', '3'))
            confidence_threshold = float(settings.get_setting('recognition_confidence_threshold', '0.7'))
            cooldown_period = int(settings.get_setting('recognition_cooldown', '2'))
            
            # Initialize variables for this frame
            recognized_faces = []
            try:
                current_time = float(time.time())
            except (TypeError, ValueError):
                current_time = 0.0
            
            # Perform face recognition if enabled and trained
            if (self.recognition_enabled and 
                face_detector.is_trained() and 
                (self.frame_count - self.last_recognition_frame) >= frame_skip):
                
                self.last_recognition_frame = self.frame_count
                
                # Recognize faces with improved confidence threshold
                # Use more strict tolerance for better accuracy
                tolerance = float(confidence_threshold) if confidence_threshold > 0.5 else 0.6
                raw_recognized_faces = face_detector.recognize_faces(frame, tolerance=tolerance)
                
                # Filter faces based on confidence and cooldown with improved accuracy
                filtered_faces = []
                for face in raw_recognized_faces:
                    face_name = face['name']
                    confidence = face['confidence']
                    
                    # Additional confidence check - require higher confidence for known faces
                    if face_name != 'Unknown':
                        # Require higher confidence for known faces to reduce false positives
                        if confidence < 0.45:  # Minimum 45% confidence for known faces
                            # Treat as unknown if confidence is too low
                            face['name'] = 'Unknown'
                            filtered_faces.append(face)
                            event_logger.log_unknown_face(
                                confidence,
                                camera_source=str(video_capture.current_source)
                            )
                            continue
                        
                        # Check cooldown period for recognized faces
                        try:
                            last_time = float(self.last_recognition_time.get(face_name, 0))
                            if float(time.time()) - last_time >= cooldown_period:
                                filtered_faces.append(face)
                                self.last_recognition_time[face_name] = float(time.time())
                                
                                # Log recognition event to session manager
                                object_type = self._get_object_type_for_name(face_name)
                                session_manager.add_recognition_event(
                                    face_name, confidence, frame, 
                                    face['location'], object_type
                                )
                                
                                # Update recent avatars display
                                self._update_recent_avatar(face_name)
                                
                                # Log to traditional event logger
                                event_logger.log_face_recognition(
                                    face_name, 
                                    confidence,
                                    camera_source=str(video_capture.current_source)
                                )
                        except (TypeError, ValueError):
                            # If time operations fail, just add face without cooldown
                            filtered_faces.append(face)
                    else:
                        # For unknown faces, still log them
                        filtered_faces.append(face)
                        
                        # Log unknown face to session manager
                        session_manager.add_recognition_event(
                            'Unknown', confidence, frame, 
                            face['location'], 'Unknown'
                        )
                        
                        # Update recent avatars display for unknown faces
                        self._update_recent_avatar('Unknown')
                        
                        event_logger.log_unknown_face(
                            confidence,
                            camera_source=str(video_capture.current_source)
                        )
                
                # Store both raw and filtered results
                recognized_faces = raw_recognized_faces  # For display
                self._last_filtered_faces = filtered_faces  # For stats and logging
                
                # Update statistics based on filtered faces
                self._update_recognition_stats(filtered_faces)
                
                # Draw face boxes on frame using raw faces for visual consistency
                frame = face_detector.draw_face_boxes(frame, recognized_faces)
            
            # Convert frame for display
            frame_rgb = frame_processor.convert_color_space(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame to fit canvas
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                frame_pil = Image.fromarray(frame_rgb)
                frame_pil.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                frame_photo = ImageTk.PhotoImage(frame_pil)
                
                # Store reference to prevent garbage collection
                self.current_frame_photo = frame_photo
                
                # Update canvas in main thread
                self.root.after_idle(self._update_video_display, frame_photo, recognized_faces)
            
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
    
    def _update_video_display(self, frame_photo, recognized_faces) -> None:
        """Update video display in main thread."""
        try:
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # Calculate center position (compatible with both old and new PIL versions)
                try:
                    photo_width = frame_photo.width() if callable(frame_photo.width) else frame_photo.width
                    photo_height = frame_photo.height() if callable(frame_photo.height) else frame_photo.height
                except:
                    # Fallback to reasonable defaults
                    photo_width = 640
                    photo_height = 480
                    
                x = (canvas_width - photo_width) // 2
                y = (canvas_height - photo_height) // 2
                
                # Clear canvas and draw frame
                self.video_canvas.delete("all")
                self.video_canvas.create_image(x, y, anchor='nw', image=frame_photo)
                
                # Store reference
                self._current_frame_photo = frame_photo
            
            # Update status displays with throttling
            self._update_status_displays_throttled(recognized_faces)
            
        except Exception as e:
            self.logger.error(f"Error updating video display: {e}")
    
    def _update_status_displays_throttled(self, recognized_faces: list) -> None:
        """Update status displays with throttling to prevent flickering."""
        try:
            # Get current time safely
            try:
                current_time = float(time.time())
            except (TypeError, ValueError):
                current_time = 0.0
            
            # Initialize tracking variables if needed
            if not hasattr(self, '_last_recognition_update'):
                self._last_recognition_update = 0.0
            if not hasattr(self, '_last_frame_time'):
                self._last_frame_time = current_time
            
            # Ensure tracking variables are floats
            try:
                self._last_recognition_update = float(self._last_recognition_update)
                self._last_frame_time = float(self._last_frame_time)
            except (TypeError, ValueError):
                self._last_recognition_update = 0.0
                self._last_frame_time = current_time
            
            # Throttle recognition display updates to every 500ms
            if current_time - self._last_recognition_update < 0.5:
                # Update FPS counter using actual capture rate
                try:
                    actual_fps = video_capture.get_actual_fps()
                    if actual_fps > 0:
                        self.fps_label.config(text=f"FPS: {actual_fps:.1f}")
                except Exception:
                    pass
                    
                self._last_frame_time = current_time
                return
            
            self._last_recognition_update = current_time
            self._last_frame_time = current_time
            
            # Update FPS using actual capture rate
            try:
                actual_fps = video_capture.get_actual_fps()
                if actual_fps > 0:
                    self.fps_label.config(text=f"FPS: {actual_fps:.1f}")
            except Exception:
                pass
            
            # Use filtered faces for counts but raw faces for display stability
            display_faces = self._last_filtered_faces if hasattr(self, '_last_filtered_faces') else recognized_faces
            
            # Update face count (use raw count for visual consistency)
            face_count = len(recognized_faces)
            self.face_count_label.config(text=f"Faces: {face_count}")
            
            # Update recognized faces list with stability
            if display_faces:
                recognized_names = [face['name'] for face in display_faces if face['name'] != 'Unknown']
                if recognized_names:
                    unique_names = list(set(recognized_names))
                    self.recognized_faces_label.config(text=f"Recognized: {', '.join(unique_names[:3])}")
                else:
                    self.recognized_faces_label.config(text="Recognized: Unknown faces only")
            else:
                # Only show "None" if no faces detected recently
                if face_count == 0:
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
    
    def _refresh_objects_log(self) -> None:
        """Refresh recognized objects log."""
        try:
            # Get database instance
            db = get_events_db()
            
            # Get current filter values
            object_name = self.object_name_var.get().strip() if hasattr(self, 'object_name_var') else None
            object_type = self.object_type_var.get() if hasattr(self, 'object_type_var') else "All"
            object_type = None if object_type == "All" else object_type
            
            # Get filtered objects
            objects = db.get_all_recognized_objects(
                object_name=object_name if object_name else None,
                object_type=object_type,
                limit=500
            )
            
            # Clear existing items
            for item in self.recognized_objects_tree.get_children():
                self.recognized_objects_tree.delete(item)
            
            # Add objects to treeview
            for obj in objects:
                self.recognized_objects_tree.insert('', 'end', values=(
                    obj['timestamp'],
                    obj['object_name'],
                    obj['object_type'],
                    f"{obj['confidence']:.2f}",
                    obj['event_id']
                ))
            
            # Update filter status
            self._update_filter_status()
            
        except Exception as e:
            self.logger.error(f"Error refreshing objects log: {e}")
    
    def _apply_object_filters(self) -> None:
        """Apply object filters and refresh the log."""
        self._refresh_objects_log()
        self.status_label.config(text="Filters applied")
    
    def _clear_object_filters(self) -> None:
        """Clear all object filters."""
        if hasattr(self, 'object_name_var'):
            self.object_name_var.set("")
        if hasattr(self, 'object_type_var'):
            self.object_type_var.set("All")
        
        self._refresh_objects_log()
        self.status_label.config(text="Filters cleared")
    
    def _update_filter_status(self) -> None:
        """Update the filter status label."""
        if not hasattr(self, 'filter_status_label'):
            return
            
        object_name = self.object_name_var.get().strip() if hasattr(self, 'object_name_var') else ""
        object_type = self.object_type_var.get() if hasattr(self, 'object_type_var') else "All"
        
        if object_name and object_type != "All":
            status = f"Filtering by name: '{object_name}', type: {object_type}"
        elif object_name:
            status = f"Filtering by name: '{object_name}'"
        elif object_type != "All":
            status = f"Filtering by type: {object_type}"
        else:
            status = "Showing all objects"
        
        self.filter_status_label.config(text=status)
    
    def _schedule_objects_refresh(self) -> None:
        """Schedule periodic refresh of objects log."""
        if hasattr(self, 'recognized_objects_tree'):
            self._refresh_objects_log()
            # Schedule next refresh in 5 seconds
            self.root.after(5000, self._schedule_objects_refresh)
    
    def _get_object_type_for_name(self, object_name: str) -> str:
        """Get the proper object type for a recognized object name."""
        if object_name == 'Unknown':
            return 'Unknown'
        
        try:
            objects_db = get_objects_db()
            # Try to find object by various name formats
            obj = None
            
            # Try matching by modelfolder pattern first (most reliable)
            all_objects = objects_db.get_all_objects()
            for db_obj in all_objects:
                # Create full name from first_name and last_name
                first_name = db_obj.get('first_name', '')
                last_name = db_obj.get('last_name', '')
                full_name = f"{last_name} {first_name}".strip()
                
                # Check if object_name contains the database object's name parts
                if full_name and full_name in object_name:
                    obj = db_obj
                    break
                # Also check individual name parts
                if first_name and first_name in object_name:
                    obj = db_obj
                    break
                if last_name and last_name in object_name:
                    obj = db_obj
                    break
                # Also check modelfolder
                modelfolder = db_obj.get('modelfolder', '')
                if modelfolder and modelfolder in object_name:
                    obj = db_obj
                    break
            
            if obj:
                # Map category number to object type
                category = obj.get('category', '4')
                category_mapping = {
                    '1': 'Resident',
                    '2': 'Staff', 
                    '3': 'Visitor',
                    '4': 'Unknown'
                }
                object_type = category_mapping.get(category, 'Unknown')
                self.logger.debug(f"Mapped {object_name} -> {object_type} (category: {category})")
                return object_type
            else:
                # Try to extract category from face name pattern (e.g., "10009 1 Sergey")
                # Pattern: [number] [category] [name]
                try:
                    parts = object_name.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        category_from_name = parts[1]
                        category_mapping = {
                            '1': 'Resident',
                            '2': 'Staff', 
                            '3': 'Visitor',
                            '4': 'Unknown'
                        }
                        object_type = category_mapping.get(category_from_name, 'Unknown')
                        self.logger.info(f"Extracted type from face name: {object_name} -> {object_type} (category: {category_from_name})")
                        return object_type
                except (IndexError, ValueError):
                    pass
                
                self.logger.warning(f"Could not find database object or extract type from name: {object_name}")
                # Default to 'Unknown' if no database match found
                return 'Unknown'
        except Exception as e:
            self.logger.error(f"Error getting object type for {object_name}: {e}")
            return 'Unknown'

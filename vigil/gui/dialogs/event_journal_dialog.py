"""
Event journal dialog for Vigil surveillance system.
Displays event sessions with photos and object information.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import os
from typing import Dict, Any, List, Optional
from vigil.database.manager import get_events_db
from vigil.utils.logging_config import get_ui_logger
from vigil.auth.authorization import authz_manager


class EventJournalDialog:
    """Dialog for viewing event journal with photos and details."""
    
    def __init__(self, root, main_window=None):
        self.root = root
        self.main_window = main_window
        self.logger = get_ui_logger()
        self.db = get_events_db()
        
        # Create dialog window
        self.dialog = tk.Toplevel(root)
        self.dialog.title("Event Journal")
        self.dialog.geometry("1200x700")
        
        # Make window resizable and enable maximize button
        self.dialog.resizable(True, True)
        self.dialog.attributes('-toolwindow', False)  # Enable maximize button
        
        # Min size to prevent UI issues
        self.dialog.minsize(800, 600)
        
        # State
        self.selected_event_id = None
        self.current_photos = []
        self.photo_thumbnails = []
        
        # Create UI
        self._create_widgets()
        self._load_events()
        
        # Handle window closing
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="5")
        main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=0)  # Button controls row
        
        # Filter controls
        self._create_filter_controls(main_frame)
        
        # Content area (events table on left, details on right)
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Events table (left side)
        self._create_events_table(content_frame)
        
        # Event details (right side)
        self._create_event_details(content_frame)
        
        # Button controls
        self._create_button_controls(main_frame)
    
    def _create_filter_controls(self, parent) -> None:
        """Create filter controls."""
        filter_frame = ttk.Frame(parent)
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        filter_frame.columnconfigure(1, weight=1)
        
        # First row - All controls including Event Delay
        controls_frame = ttk.Frame(filter_frame)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Date filters
        ttk.Label(controls_frame, text="From:").pack(side=tk.LEFT, padx=(0, 5))
        self.start_date_var = tk.StringVar()
        self.start_date_entry = ttk.Entry(controls_frame, textvariable=self.start_date_var, width=12)
        self.start_date_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(controls_frame, text="To:").pack(side=tk.LEFT, padx=(0, 5))
        self.end_date_var = tk.StringVar()
        self.end_date_entry = ttk.Entry(controls_frame, textvariable=self.end_date_var, width=12)
        self.end_date_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Filter buttons
        ttk.Button(controls_frame, text="Filter", command=self._apply_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Clear", command=self._clear_filter).pack(side=tk.LEFT, padx=(0, 10))
        
        # Event delay setting (admin only) - moved to first row
        if self.main_window and authz_manager.has_permission(self.main_window.current_role, 'admin_access'):
            ttk.Label(controls_frame, text="Event Delay (s):", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(10, 5))
            self.delay_var = tk.StringVar(value="10")
            delay_entry = ttk.Entry(controls_frame, textvariable=self.delay_var, width=5)
            delay_entry.pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(controls_frame, text="Update", command=self._update_delay).pack(side=tk.LEFT)
    
    def _create_events_table(self, parent) -> None:
        """Create events table."""
        # Events frame
        events_frame = ttk.LabelFrame(parent, text="Events", padding="5")
        events_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        events_frame.columnconfigure(0, weight=1)
        events_frame.rowconfigure(0, weight=1)
        
        # Treeview for events
        columns = ('id', 'start_time', 'duration', 'description')
        self.events_tree = ttk.Treeview(events_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.events_tree.heading('id', text='Event #')
        self.events_tree.heading('start_time', text='Start Time')
        self.events_tree.heading('duration', text='Duration (s)')
        self.events_tree.heading('description', text='Description')
        
        # Configure column widths
        self.events_tree.column('id', width=80)
        self.events_tree.column('start_time', width=150)
        self.events_tree.column('duration', width=100)
        self.events_tree.column('description', width=150)
        
        # Scrollbar
        events_scrollbar = ttk.Scrollbar(events_frame, orient=tk.VERTICAL, command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=events_scrollbar.set)
        
        # Grid widgets
        self.events_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        events_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Bind selection event
        self.events_tree.bind('<<TreeviewSelect>>', self._on_event_select)
    
    def _create_event_details(self, parent) -> None:
        """Create event details panel."""
        # Details frame
        details_frame = ttk.Frame(parent)
        details_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(1, weight=1)
        
        # Event info
        info_frame = ttk.LabelFrame(details_frame, text="Event Information", padding="5")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        info_frame.columnconfigure(1, weight=1)
        
        ttk.Label(info_frame, text="Event ID:").grid(row=0, column=0, sticky=tk.W)
        self.event_id_label = ttk.Label(info_frame, text="-")
        self.event_id_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(info_frame, text="Start Time:").grid(row=1, column=0, sticky=tk.W)
        self.start_time_label = ttk.Label(info_frame, text="-")
        self.start_time_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(info_frame, text="Duration:").grid(row=2, column=0, sticky=tk.W)
        self.duration_label = ttk.Label(info_frame, text="-")
        self.duration_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Objects table
        objects_frame = ttk.LabelFrame(details_frame, text="Recognized Objects", padding="5")
        objects_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        objects_frame.columnconfigure(0, weight=1)
        objects_frame.rowconfigure(0, weight=1)
        
        # Treeview for objects
        object_columns = ('timestamp', 'object_name', 'object_type', 'confidence')
        self.objects_tree = ttk.Treeview(objects_frame, columns=object_columns, show='headings', height=8)
        
        # Define headings
        self.objects_tree.heading('timestamp', text='Time')
        self.objects_tree.heading('object_name', text='Object Name')
        self.objects_tree.heading('object_type', text='Type')
        self.objects_tree.heading('confidence', text='Confidence')
        
        # Configure column widths
        self.objects_tree.column('timestamp', width=120)
        self.objects_tree.column('object_name', width=120)
        self.objects_tree.column('object_type', width=80)
        self.objects_tree.column('confidence', width=80)
        
        # Scrollbar for objects
        objects_scrollbar = ttk.Scrollbar(objects_frame, orient=tk.VERTICAL, command=self.objects_tree.yview)
        self.objects_tree.configure(yscrollcommand=objects_scrollbar.set)
        
        # Grid widgets
        self.objects_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        objects_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Photos frame
        photos_frame = ttk.LabelFrame(details_frame, text="Event Photos", padding="5")
        photos_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        photos_frame.columnconfigure(0, weight=1)
        photos_frame.rowconfigure(0, weight=1)
        
        # Photos canvas with scrollbar
        self.photos_canvas = tk.Canvas(photos_frame, bg='white')
        photos_scrollbar = ttk.Scrollbar(photos_frame, orient=tk.HORIZONTAL, command=self.photos_canvas.xview)
        self.photos_canvas.configure(xscrollcommand=photos_scrollbar.set)
        
        self.photos_frame_inner = ttk.Frame(self.photos_canvas)
        self.photos_canvas.create_window((0, 0), window=self.photos_frame_inner, anchor='nw')
        
        # Grid widgets
        self.photos_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        photos_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind canvas events
        self.photos_frame_inner.bind('<Configure>', self._on_photos_frame_configure)
        self.photos_canvas.bind('<Configure>', self._on_photos_canvas_configure)
    
    def _create_button_controls(self, parent) -> None:
        """Create button controls."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Left buttons
        ttk.Button(button_frame, text="Refresh", command=self._load_events).pack(side=tk.LEFT, padx=(0, 5))
        
        if self.main_window and authz_manager.has_permission(self.main_window.current_role, 'admin'):
            ttk.Button(button_frame, text="Delete Event", command=self._delete_event).pack(side=tk.LEFT, padx=(0, 5))
        
        # Right buttons
        ttk.Button(button_frame, text="Export", command=self._export_event).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Close", command=self._on_closing).pack(side=tk.RIGHT)
    
    def _load_events(self) -> None:
        """Load events from database."""
        try:
            # Clear existing items
            for item in self.events_tree.get_children():
                self.events_tree.delete(item)
            
            # Get events from database
            events = self.db.get_event_sessions(limit=200)
            
            # Add events to tree
            for event in events:
                event_id = event['id']
                start_time = event['start_time']
                duration = event.get('duration', 0)
                description = event.get('description', f'event{event_id:05d}')
                
                # Format duration properly
                if duration and duration > 0:
                    duration_str = f"{duration}s"
                elif event.get('end_time') is None:
                    duration_str = "Active"
                else:
                    duration_str = "0s"
                
                # Fix description for active sessions
                if description == "active-session" and event.get('end_time') is not None:
                    # Session ended but description wasn't updated - create proper description
                    objects = self.db.get_event_objects(event_id)
                    object_count = len(set(obj['object_name'] for obj in objects))
                    description = f"event{event_id:05d}-{object_count}-objects"
                
                self.events_tree.insert('', 'end', values=(
                    event_id, start_time, duration_str, description
                ))
            
            self.logger.info(f"Loaded {len(events)} events")
            
        except Exception as e:
            self.logger.error(f"Error loading events: {e}")
            messagebox.showerror("Error", f"Failed to load events: {e}")
    
    def _on_event_select(self, event) -> None:
        """Handle event selection."""
        selection = self.events_tree.selection()
        if not selection:
            return
        
        item = self.events_tree.item(selection[0])
        values = item['values']
        
        if not values:
            return
        
        self.selected_event_id = values[0]
        self._load_event_details(self.selected_event_id)
    
    def _load_event_details(self, event_id: int) -> None:
        """Load details for selected event."""
        try:
            # Get event session
            session = self.db.get_event_session(event_id)
            if not session:
                return
            
            # Update info labels
            self.event_id_label.config(text=str(event_id))
            self.start_time_label.config(text=session['start_time'])
            self.duration_label.config(text=f"{session.get('duration', 0)} seconds")
            
            # Load objects
            self._load_event_objects(event_id)
            
            # Load photos
            self._load_event_photos(event_id)
            
        except Exception as e:
            self.logger.error(f"Error loading event details: {e}")
    
    def _load_event_objects(self, event_id: int) -> None:
        """Load objects for selected event."""
        try:
            # Clear existing items
            for item in self.objects_tree.get_children():
                self.objects_tree.delete(item)
            
            # Get objects from database
            objects = self.db.get_event_objects(event_id)
            
            # Add objects to tree
            for obj in objects:
                timestamp = obj['timestamp']
                object_name = obj['object_name']
                object_type = obj.get('object_type', 'Person')
                confidence = f"{obj.get('confidence', 0):.2f}"
                
                self.objects_tree.insert('', 'end', values=(
                    timestamp, object_name, object_type, confidence
                ))
            
        except Exception as e:
            self.logger.error(f"Error loading event objects: {e}")
    
    def _load_event_photos(self, event_id: int) -> None:
        """Load photos for selected event."""
        try:
            # Clear existing photos
            for widget in self.photos_frame_inner.winfo_children():
                widget.destroy()
            
            self.photo_thumbnails.clear()
            
            # Get photos from database
            photos = self.db.get_event_photos(event_id)
            
            if not photos:
                # Show no photos message
                ttk.Label(self.photos_frame_inner, text="No photos available", 
                         font=('Arial', 10)).pack(pady=20)
                return
            
            # Create photo thumbnails
            for i, photo in enumerate(photos):
                photo_path = photo['photo_path']
                
                if os.path.exists(photo_path):
                    self._create_photo_thumbnail(photo_path, photo, i)
                else:
                    self.logger.warning(f"Photo file not found: {photo_path}")
            
        except Exception as e:
            self.logger.error(f"Error loading event photos: {e}")
    
    def _create_photo_thumbnail(self, photo_path: str, photo_data: Dict, index: int) -> None:
        """Create a photo thumbnail."""
        try:
            # Load and resize image
            image = Image.open(photo_path)
            image.thumbnail((100, 100), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            # Store reference to prevent garbage collection
            self.photo_thumbnails.append(photo)
            
            # Create frame for photo
            photo_frame = ttk.Frame(self.photos_frame_inner, relief=tk.RAISED, borderwidth=1)
            photo_frame.grid(row=0, column=index, padx=5, pady=5)
            
            # Photo label
            photo_label = ttk.Label(photo_frame, image=photo)
            photo_label.pack()
            
            # Info label
            info_text = f"{photo_data['object_name']}\n{photo_data['timestamp']}"
            info_label = ttk.Label(photo_frame, text=info_text, font=('Arial', 8))
            info_label.pack()
            
        except Exception as e:
            self.logger.error(f"Error creating photo thumbnail: {e}")
    
    def _on_photos_frame_configure(self, event) -> None:
        """Handle photos frame configure event."""
        # Update scroll region
        self.photos_canvas.configure(scrollregion=self.photos_canvas.bbox('all'))
    
    def _on_photos_canvas_configure(self, event) -> None:
        """Handle photos canvas configure event."""
        # Update canvas width
        canvas_width = event.width
        self.photos_canvas.itemconfig(self.photos_canvas.find_all()[0], width=canvas_width)
    
    def _apply_filter(self) -> None:
        """Apply date filter to events."""
        # This is a simplified filter implementation
        # In a full implementation, you'd modify the database query
        messagebox.showinfo("Filter", "Date filtering not yet implemented")
    
    def _clear_filter(self) -> None:
        """Clear date filter."""
        self.start_date_var.set("")
        self.end_date_var.set("")
        self._load_events()
    
    def _update_delay(self) -> None:
        """Update event inactivity delay."""
        try:
            delay = int(self.delay_var.get())
            if delay < 1:
                messagebox.showerror("Error", "Delay must be at least 1 second")
                return
            
            # Update session manager delay
            from vigil.events.session_manager import session_manager
            session_manager.set_inactivity_delay(delay)
            
            messagebox.showinfo("Success", f"Event delay updated to {delay} seconds")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")
    
    def _delete_event(self) -> None:
        """Delete selected event."""
        if not self.selected_event_id:
            messagebox.showwarning("Warning", "Please select an event to delete")
            return
        
        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete event {self.selected_event_id}?\n"
                              "This will permanently delete all associated photos and data."):
            try:
                # Delete from database
                success = self.db.delete_event_session(self.selected_event_id)
                
                if success:
                    messagebox.showinfo("Success", f"Event {self.selected_event_id} deleted")
                    self._load_events()
                    self._clear_event_details()
                else:
                    messagebox.showerror("Error", "Failed to delete event")
                    
            except Exception as e:
                self.logger.error(f"Error deleting event: {e}")
                messagebox.showerror("Error", f"Failed to delete event: {e}")
    
    def _export_event(self) -> None:
        """Export selected event data."""
        if not self.selected_event_id:
            messagebox.showwarning("Warning", "Please select an event to export")
            return
        
        try:
            # Choose export location
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"event_{self.selected_event_id:05d}_export.txt"
            )
            
            if not filename:
                return
            
            # Export event data
            self._export_event_to_file(self.selected_event_id, filename)
            
            messagebox.showinfo("Success", f"Event exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error exporting event: {e}")
            messagebox.showerror("Error", f"Failed to export event: {e}")
    
    def _export_event_to_file(self, event_id: int, filename: str) -> None:
        """Export event data to file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Get event data
                session = self.db.get_event_session(event_id)
                objects = self.db.get_event_objects(event_id)
                photos = self.db.get_event_photos(event_id)
                
                # Write event header
                f.write(f"Event Export: {event_id:05d}\n")
                f.write("=" * 50 + "\n\n")
                
                if session:
                    f.write(f"Event ID: {event_id}\n")
                    f.write(f"Start Time: {session['start_time']}\n")
                    f.write(f"End Time: {session.get('end_time', 'N/A')}\n")
                    f.write(f"Duration: {session.get('duration', 0)} seconds\n")
                    f.write(f"Description: {session.get('description', 'N/A')}\n\n")
                
                # Write objects
                f.write("Recognized Objects:\n")
                f.write("-" * 20 + "\n")
                for obj in objects:
                    f.write(f"Time: {obj['timestamp']}\n")
                    f.write(f"Name: {obj['object_name']}\n")
                    f.write(f"Type: {obj.get('object_type', 'Person')}\n")
                    f.write(f"Confidence: {obj.get('confidence', 0):.2f}\n")
                    f.write("-" * 10 + "\n")
                
                # Write photos
                f.write("\nPhotos:\n")
                f.write("-" * 20 + "\n")
                for photo in photos:
                    f.write(f"Time: {photo['timestamp']}\n")
                    f.write(f"Object: {photo['object_name']}\n")
                    f.write(f"Path: {photo['photo_path']}\n")
                    f.write(f"Confidence: {photo.get('confidence', 0):.2f}\n")
                    f.write("-" * 10 + "\n")
                    
        except Exception as e:
            raise Exception(f"Failed to export event: {e}")
    
    def _clear_event_details(self) -> None:
        """Clear event details panel."""
        self.selected_event_id = None
        
        # Clear info labels
        self.event_id_label.config(text="-")
        self.start_time_label.config(text="-")
        self.duration_label.config(text="-")
        
        # Clear objects tree
        for item in self.objects_tree.get_children():
            self.objects_tree.delete(item)
        
        # Clear photos
        for widget in self.photos_frame_inner.winfo_children():
            widget.destroy()
        self.photo_thumbnails.clear()
    
    def _on_closing(self) -> None:
        """Handle dialog closing."""
        self.dialog.destroy()

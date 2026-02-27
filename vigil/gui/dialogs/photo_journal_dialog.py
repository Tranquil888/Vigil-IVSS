"""
Photo Journal dialog for Vigil surveillance system.
Displays all captured photos with filtering and management capabilities.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from vigil.database.manager import get_events_db
from vigil.utils.logging_config import get_ui_logger
from vigil.gui.dialogs.person_selection_dialog import PersonSelectionDialog
from vigil.utils.dataset_manager import DatasetManager
from vigil.config.constants import get_data_dir


class PhotoJournalDialog:
    """Dialog for viewing and managing all captured photos."""
    
    def __init__(self, parent, main_window=None):
        """
        Initialize photo journal dialog.
        
        Args:
            parent: Parent window
            main_window: Main window instance for training service access
        """
        self.parent = parent
        self.main_window = main_window
        self.logger = get_ui_logger()
        self.db = get_events_db()
        self.dataset_manager = DatasetManager()
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Photo Journal")
        self.dialog.geometry("1400x900")
        
        # Make window resizable
        self.dialog.resizable(True, True)
        self.dialog.minsize(1000, 700)
        
        # State
        self.current_photos = []
        self.photo_thumbnails = []
        self.selected_photos = set()  # Track selected photos
        self.current_offset = 0
        self.photos_per_page = 100
        
        # Filter state
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()
        self.object_name_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Create UI
        self._create_widgets()
        self._load_available_dates()
        self._load_photos()
        
        # Handle window closing
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Make dialog transient to main window
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
    
    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Main container
        main_container = ttk.Frame(self.dialog)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_container, text="Photo Journal", 
                              font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Filter controls frame
        filter_frame = ttk.LabelFrame(main_container, text="Filters", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Date filters
        date_frame = ttk.Frame(filter_frame)
        date_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(date_frame, text="From Date:").pack(side=tk.LEFT, padx=(0, 5))
        self.date_from_combo = ttk.Combobox(date_frame, textvariable=self.date_from_var, width=15)
        self.date_from_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(date_frame, text="To Date:").pack(side=tk.LEFT, padx=(0, 5))
        self.date_to_combo = ttk.Combobox(date_frame, textvariable=self.date_to_var, width=15)
        self.date_to_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # Object filters
        object_frame = ttk.Frame(filter_frame)
        object_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(object_frame, text="Object Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.object_name_entry = ttk.Entry(object_frame, textvariable=self.object_name_var, width=20)
        self.object_name_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # Filter buttons
        button_frame = ttk.Frame(filter_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Apply Filters", 
                 command=self._apply_filters).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear Filters", 
                 command=self._clear_filters).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Refresh", 
                 command=self._load_photos).pack(side=tk.LEFT, padx=(0, 5))
        
        # Management buttons
        manage_frame = ttk.Frame(filter_frame)
        manage_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.delete_button = ttk.Button(manage_frame, text="Delete Selected", 
                                   command=self._delete_selected, state="disabled")
        self.delete_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.add_to_dataset_button = ttk.Button(manage_frame, text="Add to Dataset", 
                                         command=self._add_to_dataset, state="disabled")
        self.add_to_dataset_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Photo display area (80-90% of window)
        photo_container = ttk.Frame(main_container)
        photo_container.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Configure photo container to use 85% of space
        photo_container.grid_rowconfigure(0, weight=1)
        photo_container.grid_columnconfigure(0, weight=1)
        
        self._create_photo_area(photo_container)
        
        # Status bar
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # Pagination controls
        self._create_pagination_controls(main_container)
    
    def _create_photo_area(self, parent) -> None:
        """Create scrollable area for photo display."""
        # Canvas with scrollbar using grid layout
        canvas_frame = ttk.Frame(parent)
        canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.photos_canvas = tk.Canvas(canvas_frame, bg='white')
        self.photos_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, 
                                   command=self.photos_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.photos_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.photos_canvas.yview)
        
        # Inner frame for photos
        self.photos_frame_inner = ttk.Frame(self.photos_canvas)
        self.photos_canvas.create_window((0, 0), window=self.photos_frame_inner, anchor='nw')
        
        # Bind configure events
        self.photos_frame_inner.bind('<Configure>', self._on_photos_frame_configure)
        self.photos_canvas.bind('<Configure>', self._on_photos_canvas_configure)
    
    def _create_pagination_controls(self, parent) -> None:
        """Create pagination controls."""
        pagination_frame = ttk.Frame(parent)
        pagination_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.prev_button = ttk.Button(pagination_frame, text="← Previous", 
                                   command=self._previous_page, state="disabled")
        self.prev_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.page_label = ttk.Label(pagination_frame, text="Page 1")
        self.page_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.next_button = ttk.Button(pagination_frame, text="Next →", 
                                   command=self._next_page, state="disabled")
        self.next_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.total_label = ttk.Label(pagination_frame, text="Total: 0 photos")
        self.total_label.pack(side=tk.RIGHT, padx=(5, 0))
    
    def _load_available_dates(self) -> None:
        """Load available dates into dropdowns."""
        try:
            dates = self.db.get_available_dates()
            
            # Add "All" option at the beginning
            all_dates = ["All"] + dates
            
            # Update dropdowns
            self.date_from_combo['values'] = all_dates
            self.date_to_combo['values'] = all_dates
            
            # Set default values
            self.date_from_var.set("All")
            self.date_to_var.set("All")
            
        except Exception as e:
            self.logger.error(f"Error loading available dates: {e}")
    
    def _load_photos(self) -> None:
        """Load photos with current filters."""
        try:
            # Get photos from database
            date_from = self.date_from_var.get()
            date_to = self.date_to_var.get()
            
            # Handle "All" option for dates
            date_from = None if date_from == "All" else date_from
            date_to = None if date_to == "All" else date_to
            
            photos = self.db.get_all_photos(
                date_from=date_from,
                date_to=date_to,
                object_name=self.object_name_var.get() or None,
                limit=self.photos_per_page,
                offset=self.current_offset
            )
            
            self.current_photos = photos
            self._display_photos()
            self._update_pagination()
            
            # Update status
            filter_status = self._get_filter_status()
            self.status_var.set(f"Loaded {len(photos)} photos{filter_status}")
            
        except Exception as e:
            self.logger.error(f"Error loading photos: {e}")
            messagebox.showerror("Error", f"Failed to load photos: {e}")
    
    def _display_photos(self) -> None:
        """Display photos in the grid layout."""
        # Clear existing photos
        for widget in self.photos_frame_inner.winfo_children():
            widget.destroy()
        self.photo_thumbnails.clear()
        
        if not self.current_photos:
            # Show no photos message
            ttk.Label(self.photos_frame_inner, text="No photos found", 
                     font=('Arial', 12)).pack(pady=50)
            return
        
        # Create photo thumbnails
        for i, photo in enumerate(self.current_photos):
            self._create_photo_thumbnail(photo, i)
    
    def _create_photo_thumbnail(self, photo_data: Dict, index: int) -> None:
        """Create a photo thumbnail with selection capability."""
        try:
            photo_path = photo_data['photo_path']
            
            if not os.path.exists(photo_path):
                self.logger.warning(f"Photo file not found: {photo_path}")
                return
            
            # Load and resize image
            image = Image.open(photo_path)
            image.thumbnail((150, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            # Store reference
            self.photo_thumbnails.append(photo)
            
            # Calculate grid position dynamically based on window width
            cols = self._calculate_photo_columns()
            row = index // cols
            col = index % cols
            
            # Create frame for photo
            photo_frame = ttk.Frame(self.photos_frame_inner, relief=tk.RAISED, borderwidth=1)
            photo_frame.grid(row=row, column=col, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Selection checkbox
            selected_var = tk.BooleanVar(value=(photo_path in self.selected_photos))
            checkbox = ttk.Checkbutton(photo_frame, variable=selected_var,
                                   command=lambda p=photo_path, v=selected_var: self._on_photo_selection(p, v))
            checkbox.pack(pady=(0, 5))
            
            # Photo label with click binding
            photo_label = ttk.Label(photo_frame, image=photo)
            photo_label.pack(pady=(0, 5))
            photo_label.bind('<Button-1>', lambda e, p=photo_path: self._on_photo_click(e, p))
            
            # Info label
            info_text = f"{photo_data['object_name']}\n{photo_data['timestamp']}"
            info_label = ttk.Label(photo_frame, text=info_text, font=('Arial', 8), wraplength=140)
            info_label.pack(pady=(0, 5))
            
        except Exception as e:
            self.logger.error(f"Error creating photo thumbnail: {e}")
    
    def _calculate_photo_columns(self) -> int:
        """Calculate optimal number of photo columns based on canvas width."""
        try:
            # Get current canvas width
            canvas_width = self.photos_canvas.winfo_width()
            
            # Minimum width per photo (including padding)
            min_photo_width = 180  # 150px image + 30px padding
            
            # Calculate columns, ensuring at least 2 and max 6
            if canvas_width > 1:  # Valid width
                cols = max(2, min(6, canvas_width // min_photo_width))
            else:
                cols = 4  # Default fallback
            
            return cols
        except:
            return 4  # Default fallback
    
    def _on_photo_click(self, event, photo_path: str) -> None:
        """Handle photo click for selection."""
        # Toggle selection
        if photo_path in self.selected_photos:
            self.selected_photos.remove(photo_path)
        else:
            self.selected_photos.add(photo_path)
        
        self._update_selection_state()
    
    def _on_photo_selection(self, photo_path: str, selection_var: tk.BooleanVar) -> None:
        """Handle photo selection via checkbox."""
        if selection_var.get():
            self.selected_photos.add(photo_path)
        else:
            self.selected_photos.discard(photo_path)
        
        self._update_selection_state()
    
    def _update_selection_state(self) -> None:
        """Update UI state based on photo selection."""
        has_selection = len(self.selected_photos) > 0
        
        # Update button states
        self.delete_button.config(state="normal" if has_selection else "disabled")
        self.add_to_dataset_button.config(state="normal" if has_selection else "disabled")
        
        # Update status
        self.status_var.set(f"Selected {len(self.selected_photos)} photo(s)")
    
    def _apply_filters(self) -> None:
        """Apply current filters and reload photos."""
        self.current_offset = 0  # Reset to first page
        self._load_photos()
    
    def _clear_filters(self) -> None:
        """Clear all filters."""
        self.date_from_var.set("All")
        self.date_to_var.set("All")
        self.object_name_var.set("")
        self.current_offset = 0
        self._load_photos()
    
    def _get_filter_status(self) -> str:
        """Get current filter status description."""
        filters = []
        
        date_from = self.date_from_var.get()
        date_to = self.date_to_var.get()
        
        if date_from and date_from != "All":
            filters.append(f"from {date_from}")
        
        if date_to and date_to != "All":
            filters.append(f"to {date_to}")
        
        if self.object_name_var.get():
            filters.append(f"object: {self.object_name_var.get()}")
        
        return f" ({', '.join(filters)})" if filters else ""
    
    def _delete_selected(self) -> None:
        """Delete selected photos."""
        if not self.selected_photos:
            messagebox.showwarning("No Selection", "Please select photos to delete.")
            return
        
        # Confirm deletion
        result = messagebox.askyesno("Confirm Delete", 
                                   f"Delete {len(self.selected_photos)} selected photo(s)?\n\nThis action cannot be undone.")
        if not result:
            return
        
        try:
            # Get photo IDs for deletion
            photo_ids = []
            for photo in self.current_photos:
                if photo['photo_path'] in self.selected_photos:
                    photo_ids.append(photo['id'])
            
            # Delete from database
            if self.db.delete_photos(photo_ids):
                # Delete from filesystem
                deleted_count = 0
                for photo_path in self.selected_photos:
                    try:
                        if os.path.exists(photo_path):
                            os.remove(photo_path)
                            deleted_count += 1
                    except Exception as e:
                        self.logger.error(f"Error deleting photo file {photo_path}: {e}")
                
                # Clear selection and reload
                self.selected_photos.clear()
                self._load_photos()
                
                messagebox.showinfo("Success", 
                                 f"Deleted {deleted_count} photo(s) successfully.")
            else:
                messagebox.showerror("Error", "Failed to delete photos from database.")
                
        except Exception as e:
            self.logger.error(f"Error deleting photos: {e}")
            messagebox.showerror("Error", f"Failed to delete photos: {e}")
    
    def _add_to_dataset(self) -> None:
        """Add selected photos to dataset."""
        if not self.selected_photos:
            messagebox.showwarning("No Selection", "Please select photos to add to dataset.")
            return
        
        try:
            # Show person selection dialog
            dataset_path = os.path.join(get_data_dir(), 'dataset')
            person_dialog = PersonSelectionDialog(self.dialog, dataset_path)
            selected_person = person_dialog.show()
            
            if not selected_person:
                return  # User cancelled
            
            # Add photos to dataset
            success_count = 0
            import time
            for i, photo_path in enumerate(self.selected_photos):
                if self.dataset_manager.add_training_image(dataset_path, selected_person, photo_path):
                    success_count += 1
                
                # Small delay for unique timestamps
                if i < len(self.selected_photos) - 1:
                    time.sleep(0.01)
            
            if success_count > 0:
                messagebox.showinfo("Success", 
                                 f"Added {success_count} photo(s) to {selected_person}'s dataset.")
                
                # Clear selection and reload
                self.selected_photos.clear()
                self._load_photos()
                
                # Ask about training
                result = messagebox.askyesno("Retrain Model", 
                                           "Would you like to retrain the face recognition model?")
                if result:
                    self._trigger_training()
            else:
                messagebox.showerror("Error", "Failed to add photos to dataset.")
                
        except Exception as e:
            self.logger.error(f"Error adding photos to dataset: {e}")
            messagebox.showerror("Error", f"Failed to add photos: {e}")
    
    def _trigger_training(self) -> None:
        """Trigger model training."""
        try:
            if hasattr(self.main_window, 'training_service'):
                training_service = self.main_window.training_service
                
                if training_service.is_training:
                    messagebox.showwarning("Training in Progress", 
                                       "Model training is already in progress.")
                    return
                
                # Start training
                success = training_service.start_training()
                if success:
                    self.status_var.set("Model training started...")
                    messagebox.showinfo("Training Started", 
                                     "Model training has started in the background.")
                else:
                    messagebox.showerror("Error", "Failed to start model training.")
            else:
                messagebox.showerror("Error", "Training service not available.")
                
        except Exception as e:
            self.logger.error(f"Error triggering training: {e}")
            messagebox.showerror("Error", f"Failed to start training: {e}")
    
    def _previous_page(self) -> None:
        """Go to previous page."""
        if self.current_offset > 0:
            self.current_offset = max(0, self.current_offset - self.photos_per_page)
            self._load_photos()
    
    def _next_page(self) -> None:
        """Go to next page."""
        if len(self.current_photos) == self.photos_per_page:
            self.current_offset += self.photos_per_page
            self._load_photos()
    
    def _update_pagination(self) -> None:
        """Update pagination controls."""
        # Calculate page info
        current_page = (self.current_offset // self.photos_per_page) + 1
        total_photos = len(self.current_photos)
        
        # Update page label
        if total_photos > 0:
            self.page_label.config(text=f"Page {current_page}")
        else:
            self.page_label.config(text="No photos")
        
        # Update button states
        self.prev_button.config(state="normal" if self.current_offset > 0 else "disabled")
        self.next_button.config(state="normal" if total_photos == self.photos_per_page else "disabled")
        
        # Update total count (simplified - would need separate query for total count)
        self.total_label.config(text=f"Showing {total_photos} photos")
    
    def _on_photos_frame_configure(self, event) -> None:
        """Handle photos frame configure event."""
        # Update scroll region
        self.photos_canvas.configure(scrollregion=self.photos_canvas.bbox('all'))
    
    def _on_photos_canvas_configure(self, event) -> None:
        """Handle canvas resize - refresh photo layout."""
        # Update canvas width
        canvas_width = event.width
        if canvas_width > 1:
            # Calculate optimal columns based on width
            min_photo_width = 180  # 150px image + 30px padding
            cols = max(2, min(6, canvas_width // min_photo_width))
            
            # Update grid columns
            for i in range(cols):
                self.photos_frame_inner.columnconfigure(i, weight=1, minsize=170)
            
            # Update canvas window width to fill available space
            canvas_items = self.photos_canvas.find_all()
            if canvas_items:
                self.photos_canvas.itemconfig(canvas_items[0], width=canvas_width)
            
            # Refresh photo layout to adapt to new width
            self._display_photos()
    
    def _on_closing(self) -> None:
        """Handle dialog closing."""
        # Release grab and destroy dialog
        self.dialog.grab_release()
        self.dialog.destroy()
    
    def show(self) -> None:
        """Show the photo journal dialog."""
        self.dialog.wait_window()

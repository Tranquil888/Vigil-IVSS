"""
Person selection dialog for adding images to dataset.
Allows users to select existing person or create new person.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
from vigil.utils.dataset_manager import DatasetManager
from vigil.utils.logging_config import get_ui_logger


class PersonSelectionDialog:
    """Dialog for selecting or creating a person for dataset images."""
    
    def __init__(self, parent, dataset_path: str):
        """
        Initialize person selection dialog.
        
        Args:
            parent: Parent window
            dataset_path: Path to the dataset directory
        """
        self.parent = parent
        self.dataset_path = dataset_path
        self.logger = get_ui_logger()
        self.dataset_manager = DatasetManager()
        
        self.selected_person = None
        self.dialog = None
        
        self._create_dialog()
        self._load_existing_people()
    
    def _create_dialog(self) -> None:
        """Create the dialog UI."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Select Person")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self._center_dialog()
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Select Person for Dataset", 
                 font=('Arial', 12, 'bold')).pack(pady=(0, 20))
        
        # Existing person selection
        ttk.Label(main_frame, text="Existing Person:").pack(anchor=tk.W)
        
        self.person_var = tk.StringVar()
        self.person_combo = ttk.Combobox(main_frame, textvariable=self.person_var, 
                                       state="readonly", width=30)
        self.person_combo.pack(pady=(5, 15), fill=tk.X)
        self.person_combo.bind('<<ComboboxSelected>>', self._on_person_selected)
        
        # Or create new person
        ttk.Label(main_frame, text="Or Create New Person:").pack(anchor=tk.W)
        
        self.new_person_var = tk.StringVar()
        self.new_person_entry = ttk.Entry(main_frame, textvariable=self.new_person_var, 
                                       width=30)
        self.new_person_entry.pack(pady=(5, 20), fill=tk.X)
        self.new_person_entry.bind('<KeyRelease>', self._on_new_person_typing)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.select_button = ttk.Button(button_frame, text="Select", 
                                   command=self._on_select, state="disabled")
        self.select_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Cancel", 
                 command=self._on_cancel).pack(side=tk.RIGHT)
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._on_select())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
    
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
    
    def _load_existing_people(self) -> None:
        """Load existing people from dataset."""
        try:
            people = self.dataset_manager.get_people_list(self.dataset_path)
            
            if people:
                self.person_combo['values'] = people
            else:
                self.person_combo['values'] = ["No existing people"]
                self.person_combo.set("No existing people")
                
        except Exception as e:
            self.logger.error(f"Error loading existing people: {e}")
            self.person_combo['values'] = ["Error loading people"]
    
    def _on_person_selected(self, event) -> None:
        """Handle person selection from combo box."""
        selection = self.person_var.get()
        if selection and selection != "No existing people" and selection != "Error loading people":
            self.new_person_var.set("")  # Clear new person entry
            self.select_button.config(state="normal")
        else:
            self.select_button.config(state="disabled")
    
    def _on_new_person_typing(self, event) -> None:
        """Handle typing in new person entry."""
        new_person = self.new_person_var.get().strip()
        
        if new_person:
            self.person_var.set("")  # Clear combo selection
            self.select_button.config(state="normal")
        else:
            # Check if combo has valid selection
            selection = self.person_var.get()
            if selection and selection != "No existing people" and selection != "Error loading people":
                self.select_button.config(state="normal")
            else:
                self.select_button.config(state="disabled")
    
    def _on_select(self) -> None:
        """Handle select button click."""
        # Check for existing person selection
        selection = self.person_var.get()
        if selection and selection != "No existing people" and selection != "Error loading people":
            self.selected_person = selection.strip()
            self.dialog.destroy()
            return
        
        # Check for new person
        new_person = self.new_person_var.get().strip()
        if new_person:
            self.selected_person = new_person
            self.dialog.destroy()
            return
        
        messagebox.showwarning("Invalid Selection", 
                           "Please select an existing person or enter a new person name.")
    
    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.selected_person = None
        self.dialog.destroy()
    
    def show(self) -> Optional[str]:
        """
        Show dialog and return selected person name.
        
        Returns:
            Selected person name or None if cancelled
        """
        self.dialog.wait_window()
        return self.selected_person

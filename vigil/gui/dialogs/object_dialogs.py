"""
Object Management Dialogs

Dialog classes for adding, editing, and deleting objects in the Vigil surveillance system.
Based on original main.py implementation with modern UI design.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from typing import Dict, Any, Optional, Callable

from vigil.models.object import Object
from vigil.services.object_service import object_service
from vigil.utils.logging_config import get_ui_logger

logger = get_ui_logger()


class BaseObjectDialog(tk.Toplevel):
    """Base class for object dialogs."""
    
    def __init__(self, parent, title: str, geometry: str = "700x600"):
        super().__init__(parent)
        self.title(title)
        self.geometry(geometry)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.object_data = {}
        
        self._create_widgets()
        self._center_window()
    
    def _center_window(self):
        """Center the dialog on parent window."""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create dialog widgets - to be overridden."""
        raise NotImplementedError
    
    def get_result(self):
        """Get dialog result."""
        return self.result


class AddObjectDialog(BaseObjectDialog):
    """Dialog for adding a new object."""
    
    def __init__(self, parent):
        super().__init__(parent, "Add Object")
    
    def _create_widgets(self):
        """Create widgets for add object dialog."""
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Personal Information
        personal_frame = ttk.LabelFrame(main_frame, text="Personal Information", padding="10")
        personal_frame.pack(fill='x', pady=(0, 10))
        
        # First Name
        ttk.Label(personal_frame, text="First Name:").grid(row=0, column=0, sticky='w', pady=2)
        self.first_name_var = tk.StringVar()
        self.first_name_entry = ttk.Entry(personal_frame, textvariable=self.first_name_var, width=30)
        self.first_name_entry.grid(row=0, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Last Name
        ttk.Label(personal_frame, text="Last Name:").grid(row=1, column=0, sticky='w', pady=2)
        self.last_name_var = tk.StringVar()
        self.last_name_entry = ttk.Entry(personal_frame, textvariable=self.last_name_var, width=30)
        self.last_name_entry.grid(row=1, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Phone
        ttk.Label(personal_frame, text="Phone:").grid(row=2, column=0, sticky='w', pady=2)
        self.phone_var = tk.StringVar()
        self.phone_entry = ttk.Entry(personal_frame, textvariable=self.phone_var, width=30)
        self.phone_entry.grid(row=2, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        personal_frame.columnconfigure(1, weight=1)
        
        # Category
        category_frame = ttk.LabelFrame(main_frame, text="Category", padding="10")
        category_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(category_frame, text="Category:").grid(row=0, column=0, sticky='w', pady=2)
        self.category_var = tk.StringVar(value="4")
        category_combo = ttk.Combobox(category_frame, textvariable=self.category_var, 
                                   values=["1-Resident", "2-Staff", "3-Visitor", "4-Unknown"],
                                   state='readonly', width=27)
        category_combo.grid(row=0, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Show category colors
        colors_frame = ttk.Frame(category_frame)
        colors_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
        
        colors_text = "🟢 Resident  🟤 Staff  🔵 Visitor  🔴 Unknown"
        ttk.Label(colors_frame, text=colors_text, font=("Arial", 9)).pack()
        
        category_frame.columnconfigure(1, weight=1)
        
        # Address Information
        address_frame = ttk.LabelFrame(main_frame, text="Address Information", padding="10")
        address_frame.pack(fill='x', pady=(0, 10))
        
        # House Number
        ttk.Label(address_frame, text="House Number:").grid(row=0, column=0, sticky='w', pady=2)
        self.house_var = tk.StringVar()
        self.house_entry = ttk.Entry(address_frame, textvariable=self.house_var, width=30)
        self.house_entry.grid(row=0, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Apartment Number
        ttk.Label(address_frame, text="Apartment:").grid(row=1, column=0, sticky='w', pady=2)
        self.apartment_var = tk.StringVar()
        self.apartment_entry = ttk.Entry(address_frame, textvariable=self.apartment_var, width=30)
        self.apartment_entry.grid(row=1, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Floor Number
        ttk.Label(address_frame, text="Floor:").grid(row=2, column=0, sticky='w', pady=2)
        self.floor_var = tk.StringVar()
        self.floor_entry = ttk.Entry(address_frame, textvariable=self.floor_var, width=30)
        self.floor_entry.grid(row=2, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        address_frame.columnconfigure(1, weight=1)
        
        # Comments
        comments_frame = ttk.LabelFrame(main_frame, text="Comments", padding="10")
        comments_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.comments_var = tk.StringVar()
        self.comments_text = tk.Text(comments_frame, height=4, width=50)
        self.comments_text.pack(fill='both', expand=True)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Button(button_frame, text="Save", command=self._add_object).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side='right', padx=5)
        
        # Set focus
        self.first_name_entry.focus()
    
    def _add_object(self):
        """Add the object."""
        try:
            # Get form data
            object_data = {
                'first_name': self.first_name_var.get().strip(),
                'last_name': self.last_name_var.get().strip(),
                'phone': self.phone_var.get().strip(),
                'category': self.category_var.get().split('-')[0],  # Get number part
                'homenumb': self.house_var.get().strip() or "0",
                'apartmentnumb': self.apartment_var.get().strip() or "0",
                'floornumb': self.floor_var.get().strip() or "0",
                'ob_komments': self.comments_text.get("1.0", tk.END).strip()
            }
            
            # Create object and validate
            obj = Object(object_data)
            
            # Add object
            success, message = object_service.add_object(obj)
            
            if success:
                messagebox.showinfo("Success", message)
                self.result = obj
                self.destroy()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            logger.error(f"Error in add object dialog: {e}")
            messagebox.showerror("Error", f"Failed to add object: {e}")


class EditObjectDialog(BaseObjectDialog):
    """Dialog for editing an existing object."""
    
    def __init__(self, parent, modelfolder: str):
        self.modelfolder = modelfolder
        self.original_object = object_service.get_object_by_folder(modelfolder)
        super().__init__(parent, f"Edit Object - {self.original_object.get_full_name() if self.original_object else 'Unknown'}", "700x700")
    
    def _create_widgets(self):
        """Create widgets for edit object dialog."""
        if not self.original_object:
            ttk.Label(self, text="Object not found").pack(pady=20)
            ttk.Button(self, text="Close", command=self.destroy).pack()
            return
        
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Personal Information
        personal_frame = ttk.LabelFrame(main_frame, text="Personal Information", padding="10")
        personal_frame.pack(fill='x', pady=(0, 10))
        
        # First Name
        ttk.Label(personal_frame, text="First Name:").grid(row=0, column=0, sticky='w', pady=2)
        self.first_name_var = tk.StringVar(value=self.original_object.first_name)
        self.first_name_entry = ttk.Entry(personal_frame, textvariable=self.first_name_var, width=30)
        self.first_name_entry.grid(row=0, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Last Name
        ttk.Label(personal_frame, text="Last Name:").grid(row=1, column=0, sticky='w', pady=2)
        self.last_name_var = tk.StringVar(value=self.original_object.last_name)
        self.last_name_entry = ttk.Entry(personal_frame, textvariable=self.last_name_var, width=30)
        self.last_name_entry.grid(row=1, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Phone
        ttk.Label(personal_frame, text="Phone:").grid(row=2, column=0, sticky='w', pady=2)
        self.phone_var = tk.StringVar(value=self.original_object.phone)
        self.phone_entry = ttk.Entry(personal_frame, textvariable=self.phone_var, width=30)
        self.phone_entry.grid(row=2, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        personal_frame.columnconfigure(1, weight=1)
        
        # Category
        category_frame = ttk.LabelFrame(main_frame, text="Category", padding="10")
        category_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(category_frame, text="Category:").grid(row=0, column=0, sticky='w', pady=2)
        category_value = f"{self.original_object.category}-{self.original_object.get_category_name()}"
        self.category_var = tk.StringVar(value=category_value)
        category_combo = ttk.Combobox(category_frame, textvariable=self.category_var,
                                   values=["1-Resident", "2-Staff", "3-Visitor", "4-Unknown"],
                                   state='readonly', width=27)
        category_combo.grid(row=0, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Show category colors
        colors_frame = ttk.Frame(category_frame)
        colors_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
        
        colors_text = "🟢 Resident  🟤 Staff  🔵 Visitor  🔴 Unknown"
        ttk.Label(colors_frame, text=colors_text, font=("Arial", 9)).pack()
        
        category_frame.columnconfigure(1, weight=1)
        
        # Address Information
        address_frame = ttk.LabelFrame(main_frame, text="Address Information", padding="10")
        address_frame.pack(fill='x', pady=(0, 10))
        
        # House Number
        ttk.Label(address_frame, text="House Number:").grid(row=0, column=0, sticky='w', pady=2)
        self.house_var = tk.StringVar(value=self.original_object.homenumb)
        self.house_entry = ttk.Entry(address_frame, textvariable=self.house_var, width=30)
        self.house_entry.grid(row=0, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Apartment Number
        ttk.Label(address_frame, text="Apartment:").grid(row=1, column=0, sticky='w', pady=2)
        self.apartment_var = tk.StringVar(value=self.original_object.apartmentnumb)
        self.apartment_entry = ttk.Entry(address_frame, textvariable=self.apartment_var, width=30)
        self.apartment_entry.grid(row=1, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        # Floor Number
        ttk.Label(address_frame, text="Floor:").grid(row=2, column=0, sticky='w', pady=2)
        self.floor_var = tk.StringVar(value=self.original_object.floornumb)
        self.floor_entry = ttk.Entry(address_frame, textvariable=self.floor_var, width=30)
        self.floor_entry.grid(row=2, column=1, sticky='ew', pady=2, padx=(10, 0))
        
        address_frame.columnconfigure(1, weight=1)
        
        # Comments
        comments_frame = ttk.LabelFrame(main_frame, text="Comments", padding="10")
        comments_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.comments_var = tk.StringVar(value=self.original_object.ob_komments)
        self.comments_text = tk.Text(comments_frame, height=4, width=50)
        self.comments_text.insert("1.0", self.original_object.ob_komments)
        self.comments_text.pack(fill='both', expand=True)
        
        # Model Folder Info
        info_frame = ttk.LabelFrame(main_frame, text="Model Information", padding="10")
        info_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(info_frame, text=f"Model Folder: {self.original_object.modelfolder}").pack(anchor='w')
        ttk.Label(info_frame, text="Note: Model folder cannot be changed").pack(anchor='w', pady=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Button(button_frame, text="Save", command=self._update_object).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side='right', padx=5)
        
        # Set focus
        self.first_name_entry.focus()
    
    def _update_object(self):
        """Update the object."""
        try:
            # Get form data
            object_data = {
                'first_name': self.first_name_var.get().strip(),
                'last_name': self.last_name_var.get().strip(),
                'phone': self.phone_var.get().strip(),
                'category': self.category_var.get().split('-')[0],  # Get number part
                'homenumb': self.house_var.get().strip() or "0",
                'apartmentnumb': self.apartment_var.get().strip() or "0",
                'floornumb': self.floor_var.get().strip() or "0",
                'ob_komments': self.comments_text.get("1.0", tk.END).strip()
            }
            
            # Create object and validate
            obj = Object(object_data)
            
            # Update object
            success, message = object_service.update_object(self.modelfolder, obj)
            
            if success:
                messagebox.showinfo("Success", message)
                self.result = obj
                self.destroy()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            logger.error(f"Error in edit object dialog: {e}")
            messagebox.showerror("Error", f"Failed to update object: {e}")


class DeleteObjectDialog(BaseObjectDialog):
    """Dialog for deleting an object."""
    
    def __init__(self, parent, modelfolder: str):
        self.modelfolder = modelfolder
        self.target_object = object_service.get_object_by_folder(modelfolder)
        super().__init__(parent, f"Delete Object - {self.target_object.get_full_name() if self.target_object else 'Unknown'}")
    
    def _create_widgets(self):
        """Create widgets for delete object dialog."""
        if not self.target_object:
            ttk.Label(self, text="Object not found").pack(pady=20)
            ttk.Button(self, text="Close", command=self.destroy).pack()
            return
        
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Warning message
        warning_frame = ttk.LabelFrame(main_frame, text="Warning", padding="10")
        warning_frame.pack(fill='x', pady=(0, 10))
        
        warning_text = f"""Are you sure you want to delete this object?

Name: {self.target_object.get_full_name()}
Category: {self.target_object.get_category_name()}
Model Folder: {self.target_object.modelfolder}

This action cannot be undone!"""
        
        ttk.Label(warning_frame, text=warning_text, justify='left').pack()
        
        # Dataset folder option
        dataset_frame = ttk.LabelFrame(main_frame, text="Dataset Folder", padding="10")
        dataset_frame.pack(fill='x', pady=(0, 10))
        
        self.remove_dataset_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dataset_frame, text="Also remove dataset folder", 
                       variable=self.remove_dataset_var).pack(anchor='w')
        
        dataset_info = f"Dataset folder: data/dataset/{self.target_object.modelfolder}"
        ttk.Label(dataset_frame, text=dataset_info, font=("Arial", 9)).pack(anchor='w', pady=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Button(button_frame, text="Delete Object", command=self._delete_object).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side='right', padx=5)
    
    def _delete_object(self):
        """Delete the object."""
        try:
            # Confirm deletion
            if not messagebox.askyesno("Confirm Delete", 
                                     f"Are you sure you want to delete '{self.target_object.get_full_name()}'?"):
                return
            
            # Delete object
            success, message = object_service.delete_object(
                self.modelfolder, 
                self.remove_dataset_var.get()
            )
            
            if success:
                messagebox.showinfo("Success", message)
                self.result = self.target_object
                self.destroy()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            logger.error(f"Error in delete object dialog: {e}")
            messagebox.showerror("Error", f"Failed to delete object: {e}")

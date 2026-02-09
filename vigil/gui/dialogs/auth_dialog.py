"""
Authentication dialog for Vigil surveillance system.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple
from vigil.auth.authentication import auth_manager
from vigil.utils.logging_config import get_auth_logger


class AuthenticationDialog:
    """Dialog for user authentication."""
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.logger = get_auth_logger()
        self.result: Optional[Tuple[str, str]] = None
        self.window = None
    
    def show(self) -> Optional[Tuple[str, str]]:
        """Show the authentication dialog and return user credentials."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Vigil - Authentication")
        self.window.geometry("400x300")
        self.window.resizable(False, False)
        
        # Center the dialog
        self._center_window()
        
        # Make dialog modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        self._create_widgets()
        
        # Focus on username entry
        self.username_entry.focus()
        
        # Wait for dialog to close
        self.window.wait_window()
        
        return self.result
    
    def _center_window(self) -> None:
        """Center the dialog on the parent window."""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.window.winfo_screenheight() // 2) - (300 // 2)
        self.window.geometry(f'400x300+{x}+{y}')
    
    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Title
        title_label = tk.Label(
            self.window,
            text="Vigil Surveillance System",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)
        
        # Subtitle
        subtitle_label = tk.Label(
            self.window,
            text="Please enter your credentials",
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=5)
        
        # Username frame
        username_frame = tk.Frame(self.window)
        username_frame.pack(pady=10, padx=20, fill='x')
        
        tk.Label(username_frame, text="Username:", font=("Arial", 10)).pack(anchor='w')
        self.username_entry = tk.Entry(username_frame, font=("Arial", 10), width=30)
        self.username_entry.pack(fill='x', pady=5)
        
        # Password frame
        password_frame = tk.Frame(self.window)
        password_frame.pack(pady=10, padx=20, fill='x')
        
        tk.Label(password_frame, text="Password:", font=("Arial", 10)).pack(anchor='w')
        self.password_entry = tk.Entry(password_frame, font=("Arial", 10), width=30, show="*")
        self.password_entry.pack(fill='x', pady=5)
        
        # Bind Enter key to login
        self.password_entry.bind('<Return>', lambda e: self._login())
        
        # Buttons frame
        buttons_frame = tk.Frame(self.window)
        buttons_frame.pack(pady=20)
        
        login_button = ttk.Button(
            buttons_frame,
            text="Login",
            command=self._login,
            width=15
        )
        login_button.pack(side='left', padx=5)
        
        cancel_button = ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self._cancel,
            width=15
        )
        cancel_button.pack(side='left', padx=5)
        
        # Status label
        self.status_label = tk.Label(
            self.window,
            text="",
            font=("Arial", 9),
            fg="red"
        )
        self.status_label.pack(pady=5)
    
    def _login(self) -> None:
        """Handle login button click."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.status_label.config(text="Please enter username and password")
            return
        
        # Authenticate user
        success, message = auth_manager.authenticate(username, password)
        
        if success:
            self.logger.info(f"User '{username}' authenticated successfully")
            
            # Get user role
            user = auth_manager.db.get_user(username)
            role = user.get('role', 'operator') if user else 'operator'
            
            self.result = (username, role)
            self.window.destroy()
        else:
            self.status_label.config(text=message)
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus()
    
    def _cancel(self) -> None:
        """Handle cancel button click."""
        self.logger.info("Authentication cancelled by user")
        self.window.destroy()


class CreateUserDialog:
    """Dialog for creating new users (admin only)."""
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.logger = get_auth_logger()
        self.result = False
        self.window = None
    
    def show(self) -> bool:
        """Show the create user dialog and return success status."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Create New User")
        self.window.geometry("400x350")
        self.window.resizable(False, False)
        
        # Center the dialog
        self._center_window()
        
        # Make dialog modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        self._create_widgets()
        
        # Focus on username entry
        self.username_entry.focus()
        
        # Wait for dialog to close
        self.window.wait_window()
        
        return self.result
    
    def _center_window(self) -> None:
        """Center the dialog on the parent window."""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.window.winfo_screenheight() // 2) - (350 // 2)
        self.window.geometry(f'400x350+{x}+{y}')
    
    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Title
        title_label = tk.Label(
            self.window,
            text="Create New User",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=15)
        
        # Username frame
        username_frame = tk.Frame(self.window)
        username_frame.pack(pady=8, padx=20, fill='x')
        
        tk.Label(username_frame, text="Username:", font=("Arial", 10)).pack(anchor='w')
        self.username_entry = tk.Entry(username_frame, font=("Arial", 10), width=30)
        self.username_entry.pack(fill='x', pady=3)
        
        # Password frame
        password_frame = tk.Frame(self.window)
        password_frame.pack(pady=8, padx=20, fill='x')
        
        tk.Label(password_frame, text="Password:", font=("Arial", 10)).pack(anchor='w')
        self.password_entry = tk.Entry(password_frame, font=("Arial", 10), width=30, show="*")
        self.password_entry.pack(fill='x', pady=3)
        
        # Confirm password frame
        confirm_frame = tk.Frame(self.window)
        confirm_frame.pack(pady=8, padx=20, fill='x')
        
        tk.Label(confirm_frame, text="Confirm Password:", font=("Arial", 10)).pack(anchor='w')
        self.confirm_entry = tk.Entry(confirm_frame, font=("Arial", 10), width=30, show="*")
        self.confirm_entry.pack(fill='x', pady=3)
        
        # Role frame
        role_frame = tk.Frame(self.window)
        role_frame.pack(pady=8, padx=20, fill='x')
        
        tk.Label(role_frame, text="Role:", font=("Arial", 10)).pack(anchor='w')
        self.role_var = tk.StringVar(value="operator")
        role_combo = ttk.Combobox(
            role_frame,
            textvariable=self.role_var,
            values=["operator", "admin"],
            state="readonly",
            width=28
        )
        role_combo.pack(fill='x', pady=3)
        
        # Buttons frame
        buttons_frame = tk.Frame(self.window)
        buttons_frame.pack(pady=15)
        
        create_button = ttk.Button(
            buttons_frame,
            text="Create",
            command=self._create_user,
            width=12
        )
        create_button.pack(side='left', padx=5)
        
        cancel_button = ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self._cancel,
            width=12
        )
        cancel_button.pack(side='left', padx=5)
        
        # Status label
        self.status_label = tk.Label(
            self.window,
            text="",
            font=("Arial", 9),
            fg="red"
        )
        self.status_label.pack(pady=5)
    
    def _create_user(self) -> None:
        """Handle create user button click."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        role = self.role_var.get()
        
        # Validation
        if not username or not password or not confirm:
            self.status_label.config(text="All fields are required")
            return
        
        if password != confirm:
            self.status_label.config(text="Passwords do not match")
            return
        
        # Create user
        success, message = auth_manager.create_user(username, password, role)
        
        if success:
            self.logger.info(f"User '{username}' created successfully")
            messagebox.showinfo("Success", f"User '{username}' created successfully")
            self.result = True
            self.window.destroy()
        else:
            self.status_label.config(text=message)
    
    def _cancel(self) -> None:
        """Handle cancel button click."""
        self.window.destroy()

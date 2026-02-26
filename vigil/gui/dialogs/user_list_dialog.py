"""
User list dialog for Vigil surveillance system.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any
from vigil.auth.authentication import auth_manager
from vigil.utils.logging_config import get_auth_logger


class UserListDialog:
    """Dialog for displaying users with role-based visibility."""
    
    def __init__(self, parent: tk.Tk, current_role: str):
        self.parent = parent
        self.current_role = current_role
        self.logger = get_auth_logger()
        self.window = None
        self.tree = None
    
    def show(self) -> None:
        """Show the user list dialog."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("User List")
        self.window.geometry("600x450")
        self.window.resizable(True, True)
        
        # Center the dialog
        self._center_window()
        
        # Make dialog modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        self._create_widgets()
        self._load_users()
        
        # Wait for dialog to close
        self.window.wait_window()
    
    def _center_window(self) -> None:
        """Center the dialog on the parent window."""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.window.winfo_screenheight() // 2) - (450 // 2)
        self.window.geometry(f'600x450+{x}+{y}')
    
    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Title label
        title_label = tk.Label(
            self.window,
            text="User Management",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=10)
        
        # Current role indicator
        role_label = tk.Label(
            self.window,
            text=f"Viewing as: {self.current_role.title()}",
            font=("Arial", 10),
            fg="blue"
        )
        role_label.pack(pady=5)
        
        # Treeview frame
        tree_frame = ttk.Frame(self.window)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create treeview with scrollbar
        self.tree = ttk.Treeview(
            tree_frame,
            columns=('username', 'role', 'created_at', 'last_login'),
            show='headings',
            height=12
        )
        
        # Configure columns
        self.tree.heading('username', text='Username')
        self.tree.heading('role', text='Role')
        self.tree.heading('created_at', text='Created At')
        self.tree.heading('last_login', text='Last Login')
        
        # Column widths
        self.tree.column('username', width=150)
        self.tree.column('role', width=100)
        self.tree.column('created_at', width=150)
        self.tree.column('last_login', width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.window)
        buttons_frame.pack(pady=10)
        
        refresh_button = ttk.Button(
            buttons_frame,
            text="Refresh",
            command=self._load_users,
            width=12
        )
        refresh_button.pack(side='left', padx=5)
        
        close_button = ttk.Button(
            buttons_frame,
            text="Close",
            command=self._close,
            width=12
        )
        close_button.pack(side='left', padx=5)
        
        # Status label
        self.status_label = tk.Label(
            self.window,
            text="",
            font=("Arial", 9),
            fg="green"
        )
        self.status_label.pack(pady=5)
    
    def _get_filtered_users(self) -> List[Dict[str, Any]]:
        """Get users filtered by current user's role."""
        try:
            all_users = auth_manager.get_all_users()
            
            if self.current_role == 'admin':
                # Admins can see all users
                return all_users
            else:
                # Operators can only see other operators (not admins)
                filtered_users = [
                    user for user in all_users 
                    if user['role'] == 'operator'
                ]
                self.logger.info(f"Operator {self.current_role} viewing {len(filtered_users)} operators")
                return filtered_users
                
        except Exception as e:
            self.logger.error(f"Error getting users: {e}")
            return []
    
    def _load_users(self) -> None:
        """Load and display users in the treeview."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get filtered users
        users = self._get_filtered_users()
        
        if not users:
            self.status_label.config(text="No users found")
            return
        
        # Add users to treeview
        for user in users:
            # Format datetime fields
            created_at = user.get('created_at') or 'N/A'
            last_login = user.get('last_login') or 'Never'
            
            # Truncate long datetime strings
            if created_at != 'N/A' and len(str(created_at)) > 19:
                created_at = str(created_at)[:19]
            if last_login != 'Never' and len(str(last_login)) > 19:
                last_login = str(last_login)[:19]
            
            self.tree.insert(
                '',
                'end',
                values=(
                    user.get('username', 'N/A'),
                    user.get('role', 'N/A'),
                    created_at,
                    last_login
                )
            )
        
        # Update status
        user_count = len(users)
        if self.current_role == 'admin':
            self.status_label.config(text=f"Showing all {user_count} users")
        else:
            self.status_label.config(text=f"Showing {user_count} operators (admins hidden)")
    
    def _close(self) -> None:
        """Close the dialog."""
        self.logger.info(f"User list dialog closed by {self.current_role}")
        self.window.destroy()

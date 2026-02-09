"""
User authentication module for Vigil surveillance system.
"""

import hashlib
from typing import Optional, Tuple
from vigil.core.exceptions import AuthenticationError, ValidationError
from vigil.utils.logging_config import get_auth_logger
from vigil.database.manager import get_auth_db


class AuthenticationManager:
    """Manages user authentication and session handling."""
    
    def __init__(self):
        self.logger = get_auth_logger()
        self.db = get_auth_db()
        self.max_attempts = 3
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def validate_password(self, password: str) -> bool:
        """Validate password requirements."""
        if len(password) < 4:
            raise ValidationError("Password must be at least 4 characters long")
        return True
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Authenticate a user with username and password.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not username or not password:
                return False, "Username and password are required"
            
            # Get user from database
            user = self.db.get_user(username)
            if not user:
                self.logger.warning(f"Authentication failed: user '{username}' not found")
                return False, "Invalid username or password"
            
            # Check login attempts
            if user.get('login_attempts', 0) >= self.max_attempts:
                self.logger.warning(f"Authentication blocked: user '{username}' exceeded max attempts")
                return False, "Account locked due to too many failed attempts"
            
            # Verify password
            password_hash = self.hash_password(password)
            if password_hash != user.get('password_hash'):
                # Increment login attempts
                attempts = user.get('login_attempts', 0) + 1
                self.db.update_login_attempt(username, attempts)
                self.logger.warning(f"Authentication failed: invalid password for user '{username}'")
                return False, "Invalid username or password"
            
            # Successful authentication
            self.db.update_last_login(username)
            self.logger.info(f"User '{username}' authenticated successfully")
            return True, "Authentication successful"
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False, "Authentication system error"
    
    def create_user(self, username: str, password: str, role: str = "operator") -> Tuple[bool, str]:
        """
        Create a new user account.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate inputs
            if not username or not password:
                return False, "Username and password are required"
            
            if len(username) < 3:
                return False, "Username must be at least 3 characters long"
            
            self.validate_password(password)
            
            if role not in ["admin", "operator"]:
                return False, "Role must be 'admin' or 'operator'"
            
            # Check if user already exists
            existing_user = self.db.get_user(username)
            if existing_user:
                return False, "Username already exists"
            
            # Create user
            password_hash = self.hash_password(password)
            success = self.db.create_user(username, password_hash, role)
            
            if success:
                self.logger.info(f"User '{username}' created with role '{role}'")
                return True, "User created successfully"
            else:
                return False, "Failed to create user"
                
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            self.logger.error(f"User creation error: {e}")
            return False, "User creation system error"
    
    def create_admin_user(self, username: str, password: str) -> Tuple[bool, str]:
        """Create the first admin user."""
        return self.create_user(username, password, "admin")
    
    def get_all_users(self) -> list:
        """Get all users (for admin interface)."""
        try:
            return self.db.get_all_users()
        except Exception as e:
            self.logger.error(f"Error getting users: {e}")
            return []
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """Delete a user account."""
        try:
            if not username:
                return False, "Username is required"
            
            success = self.db.delete_user(username)
            if success:
                self.logger.info(f"User '{username}' deleted")
                return True, "User deleted successfully"
            else:
                return False, "User not found"
                
        except Exception as e:
            self.logger.error(f"User deletion error: {e}")
            return False, "User deletion system error"
    
    def reset_login_attempts(self, username: str) -> bool:
        """Reset login attempts for a user."""
        try:
            self.db.update_login_attempt(username, 0)
            self.logger.info(f"Login attempts reset for user '{username}'")
            return True
        except Exception as e:
            self.logger.error(f"Error resetting login attempts: {e}")
            return False


# Global authentication instance
auth_manager = AuthenticationManager()

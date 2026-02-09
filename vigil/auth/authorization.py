"""
Authorization and role-based access control for Vigil surveillance system.
"""

from typing import List, Dict, Any
from vigil.core.exceptions import AuthorizationError
from vigil.utils.logging_config import get_auth_logger
from vigil.config.constants import ROLE_ADMIN, ROLE_OPERATOR


class AuthorizationManager:
    """Manages role-based access control."""
    
    def __init__(self):
        self.logger = get_auth_logger()
        self._setup_permissions()
    
    def _setup_permissions(self) -> None:
        """Setup role permissions mapping."""
        self.permissions = {
            ROLE_ADMIN: {
                # User management
                'create_user', 'delete_user', 'view_users', 'edit_user',
                # Object management
                'create_object', 'delete_object', 'edit_object', 'view_objects',
                'train_model', 'view_dataset',
                # Camera management
                'add_camera', 'edit_camera', 'delete_camera', 'view_cameras',
                # System settings
                'edit_settings', 'view_settings',
                # Video operations
                'start_recording', 'stop_recording', 'view_video',
                'start_streaming', 'stop_streaming',
                # Event management
                'view_events', 'export_events', 'delete_events',
                # Full access
                'admin_access'
            },
            ROLE_OPERATOR: {
                # Limited object management
                'view_objects', 'edit_object',
                # Camera viewing only
                'view_cameras',
                # Video operations
                'start_recording', 'stop_recording', 'view_video',
                'start_streaming', 'stop_streaming',
                # Event management
                'view_events', 'export_events',
                # No user management or system settings
            }
        }
    
    def has_permission(self, user_role: str, permission: str) -> bool:
        """
        Check if a user role has a specific permission.
        
        Args:
            user_role: The user's role ('admin' or 'operator')
            permission: The permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        if user_role not in self.permissions:
            self.logger.warning(f"Unknown user role: {user_role}")
            return False
        
        return permission in self.permissions[user_role]
    
    def check_permission(self, user_role: str, permission: str) -> None:
        """
        Check permission and raise exception if not authorized.
        
        Raises:
            AuthorizationError: If user doesn't have permission
        """
        if not self.has_permission(user_role, permission):
            raise AuthorizationError(f"User role '{user_role}' does not have permission '{permission}'")
    
    def get_user_permissions(self, user_role: str) -> List[str]:
        """Get all permissions for a user role."""
        return list(self.permissions.get(user_role, []))
    
    def can_manage_users(self, user_role: str) -> bool:
        """Check if user can manage other users."""
        return self.has_permission(user_role, 'create_user')
    
    def can_manage_objects(self, user_role: str) -> bool:
        """Check if user can manage objects."""
        return self.has_permission(user_role, 'create_object')
    
    def can_manage_cameras(self, user_role: str) -> bool:
        """Check if user can manage cameras."""
        return self.has_permission(user_role, 'add_camera')
    
    def can_edit_settings(self, user_role: str) -> bool:
        """Check if user can edit system settings."""
        return self.has_permission(user_role, 'edit_settings')
    
    def can_train_model(self, user_role: str) -> bool:
        """Check if user can train recognition model."""
        return self.has_permission(user_role, 'train_model')
    
    def can_view_events(self, user_role: str) -> bool:
        """Check if user can view events."""
        return self.has_permission(user_role, 'view_events')
    
    def can_export_events(self, user_role: str) -> bool:
        """Check if user can export events."""
        return self.has_permission(user_role, 'export_events')
    
    def can_record_video(self, user_role: str) -> bool:
        """Check if user can record video."""
        return self.has_permission(user_role, 'start_recording')
    
    def can_stream_video(self, user_role: str) -> bool:
        """Check if user can stream video."""
        return self.has_permission(user_role, 'start_streaming')


# Global authorization instance
authz_manager = AuthorizationManager()

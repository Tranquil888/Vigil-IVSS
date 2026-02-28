"""
Object Service Layer

Business logic for object management in the Vigil surveillance system.
Coordinates between UI and database layers.
"""

import os
from typing import List, Dict, Any, Optional, Tuple

from vigil.database.objects_manager import objects_manager
from vigil.models.object import Object
from vigil.utils.logging_config import get_service_logger

logger = get_service_logger()


class ObjectService:
    """Service layer for object management operations."""
    
    def __init__(self):
        """Initialize object service."""
        self.objects_manager = objects_manager
    
    def get_all_objects(self) -> List[Object]:
        """Get all objects from the system."""
        try:
            objects_data = self.objects_manager.get_all_objects()
            objects = [Object(data) for data in objects_data]
            logger.debug(f"Retrieved {len(objects)} objects")
            return objects
        except Exception as e:
            logger.error(f"Failed to get objects: {e}")
            return []
    
    def get_object_by_folder(self, modelfolder: str) -> Optional[Object]:
        """Get object by model folder name."""
        try:
            object_data = self.objects_manager.get_object_by_folder(modelfolder)
            if object_data:
                return Object(object_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get object by folder {modelfolder}: {e}")
            return None
    
    def add_object(self, obj: Object) -> Tuple[bool, str]:
        """Add a new object to the system."""
        try:
            # Validate object
            is_valid, error_message = obj.validate()
            if not is_valid:
                return False, error_message
            
            # Generate model folder
            next_number = self._get_next_object_number()
            obj.modelfolder = obj.generate_model_folder(next_number)
            
            # Set avatar based on category only if no custom avatar is provided
            if not obj.foto or obj.foto == "no_avatar_red.jpg":
                obj.foto = obj.get_avatar_filename()
            
            # Add to database
            success, message = self.objects_manager.add_object(obj.to_dict())
            
            if success:
                logger.info(f"Added new object: {obj.get_full_name()}")
                return True, message
            else:
                logger.error(f"Failed to add object: {message}")
                return False, message
                
        except Exception as e:
            logger.error(f"Failed to add object: {e}")
            return False, f"Service error: {e}"
    
    def update_object(self, modelfolder: str, obj: Object) -> Tuple[bool, str]:
        """Update an existing object."""
        try:
            # Validate object
            is_valid, error_message = obj.validate()
            if not is_valid:
                return False, error_message
            
            # Update avatar only if no custom avatar is provided or if it was a default avatar
            if not obj.foto or obj.foto in ['no_avatar_green.jpg', 'no_avatar_grey.jpg', 'no_avatar_blue.jpg', 'no_avatar_red.jpg']:
                obj.foto = obj.get_avatar_filename()
            
            # Update in database
            success, message = self.objects_manager.update_object(modelfolder, obj.to_dict())
            
            if success:
                logger.info(f"Updated object: {obj.get_full_name()}")
                return True, message
            else:
                logger.error(f"Failed to update object: {message}")
                return False, message
                
        except Exception as e:
            logger.error(f"Failed to update object: {e}")
            return False, f"Service error: {e}"
    
    def delete_object(self, modelfolder: str, remove_dataset: bool = False) -> Tuple[bool, str]:
        """Delete an object from the system."""
        try:
            # Get object info for logging
            obj = self.get_object_by_folder(modelfolder)
            if not obj:
                return False, "Object not found"
            
            if not obj.is_deletable():
                return False, "Cannot delete system object"
            
            # Delete from database
            success, message = self.objects_manager.delete_object(modelfolder)
            
            if success:
                # Remove dataset folder if requested
                if remove_dataset:
                    self.objects_manager._remove_dataset_folder(modelfolder)
                    message += " (dataset folder removed)"
                
                logger.info(f"Deleted object: {obj.get_full_name()}")
                return True, message
            else:
                logger.error(f"Failed to delete object: {message}")
                return False, message
                
        except Exception as e:
            logger.error(f"Failed to delete object: {e}")
            return False, f"Service error: {e}"
    
    def get_object_statistics(self) -> Dict[str, Any]:
        """Get statistics about objects in the system."""
        try:
            objects = self.get_all_objects()
            
            stats = {
                'total_objects': len(objects),
                'by_category': {},
                'with_dataset_folders': 0,
                'editable_objects': 0
            }
            
            for obj in objects:
                # Count by category
                category_name = obj.get_category_name()
                stats['by_category'][category_name] = stats['by_category'].get(category_name, 0) + 1
                
                # Count objects with dataset folders
                if obj.modelfolder and obj.modelfolder != "Unknown":
                    stats['with_dataset_folders'] += 1
                
                # Count editable objects
                if obj.is_editable():
                    stats['editable_objects'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get object statistics: {e}")
            return {}
    
    def search_objects(self, query: str) -> List[Object]:
        """Search objects by name or other fields."""
        try:
            if not query:
                return self.get_all_objects()
            
            objects = self.get_all_objects()
            query_lower = query.lower()
            
            filtered_objects = []
            for obj in objects:
                # Search in multiple fields
                searchable_text = f"{obj.first_name} {obj.last_name} {obj.phone} {obj.ob_komments}".lower()
                if query_lower in searchable_text:
                    filtered_objects.append(obj)
            
            logger.debug(f"Search for '{query}' returned {len(filtered_objects)} results")
            return filtered_objects
            
        except Exception as e:
            logger.error(f"Failed to search objects: {e}")
            return []
    
    def export_objects(self, file_path: str) -> Tuple[bool, str]:
        """Export objects to CSV file."""
        try:
            import csv
            
            objects = self.get_all_objects()
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'first_name', 'last_name', 'phone', 'category',
                    'homenumb', 'apartmentnumb', 'floornumb',
                    'modelfolder', 'foto', 'userlink', 'ob_komments'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for obj in objects:
                    writer.writerow(obj.to_dict())
            
            logger.info(f"Exported {len(objects)} objects to {file_path}")
            return True, f"Successfully exported {len(objects)} objects"
            
        except Exception as e:
            logger.error(f"Failed to export objects: {e}")
            return False, f"Export failed: {e}"
    
    def _get_next_object_number(self) -> int:
        """Get next available object number."""
        try:
            registry_path = os.path.join(
                os.path.dirname(self.objects_manager.db_path), 
                '..', 'numberreestr.txt'
            )
            
            if os.path.exists(registry_path):
                with open(registry_path, 'r') as f:
                    number = int(f.read().strip()) + 1
            else:
                number = 10000
            
            with open(registry_path, 'w') as f:
                f.write(str(number))
            
            return number
            
        except Exception as e:
            logger.error(f"Failed to get next object number: {e}")
            return 10000


# Global service instance
object_service = ObjectService()

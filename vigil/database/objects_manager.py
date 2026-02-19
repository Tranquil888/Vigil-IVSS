"""
Objects Database Manager

Handles all database operations for object management in the Vigil surveillance system.
Based on the original main.py implementation but adapted for modular architecture.
"""

import os
import sqlite3
import re
from typing import List, Dict, Any, Optional, Tuple
from transliterate import translit

from vigil.config.constants import OBJECTS_DB_PATH
from vigil.utils.logging_config import get_database_logger

logger = get_database_logger()


class ObjectsManager:
    """Manages object database operations."""
    
    def __init__(self, db_path: str = OBJECTS_DB_PATH):
        """Initialize the objects database manager."""
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Create database and tables if they don't exist."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create People table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS People (
                last_name TEXT,
                first_name TEXT,
                phone TEXT,
                category TEXT,
                homenumb TEXT,
                apartmentnumb TEXT,
                floornumb TEXT,
                modelfolder TEXT,
                foto TEXT,
                userlink TEXT,
                ob_komments TEXT,
                ob_sets01 TEXT,
                ob_sets02 TEXT,
                ob_sets03 TEXT,
                ob_sets04 TEXT,
                ob_sets05 TEXT
            )
            ''')
            
            # Insert default Unknown record if it doesn't exist
            cursor.execute('SELECT COUNT(*) FROM People WHERE modelfolder = ?', ('Unknown',))
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                INSERT INTO People (last_name, category, modelfolder, foto) 
                VALUES (?, ?, ?, ?)
                ''', ('Unknown', '4', 'Unknown', 'no_avatar_grey.jpg'))
            
            conn.commit()
            conn.close()
            logger.info("Objects database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize objects database: {e}")
            raise
    
    def get_all_objects(self) -> List[Dict[str, Any]]:
        """Get all objects from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT last_name, first_name, phone, category, homenumb, 
                   apartmentnumb, floornumb, modelfolder, foto, userlink, 
                   ob_komments, ob_sets01, ob_sets02, ob_sets03, ob_sets04, ob_sets05
            FROM People 
            ORDER BY last_name, first_name
            ''')
            
            columns = ['last_name', 'first_name', 'phone', 'category', 'homenumb',
                      'apartmentnumb', 'floornumb', 'modelfolder', 'foto', 'userlink',
                      'ob_komments', 'ob_sets01', 'ob_sets02', 'ob_sets03', 'ob_sets04', 'ob_sets05']
            
            objects = []
            for row in cursor.fetchall():
                obj = dict(zip(columns, row))
                objects.append(obj)
            
            conn.close()
            logger.debug(f"Retrieved {len(objects)} objects from database")
            return objects
            
        except Exception as e:
            logger.error(f"Failed to get objects: {e}")
            return []
    
    def get_object_by_folder(self, modelfolder: str) -> Optional[Dict[str, Any]]:
        """Get object by model folder name."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT last_name, first_name, phone, category, homenumb, 
                   apartmentnumb, floornumb, modelfolder, foto, userlink, 
                   ob_komments, ob_sets01, ob_sets02, ob_sets03, ob_sets04, ob_sets05
            FROM People 
            WHERE modelfolder = ?
            ''', (modelfolder,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = ['last_name', 'first_name', 'phone', 'category', 'homenumb',
                          'apartmentnumb', 'floornumb', 'modelfolder', 'foto', 'userlink',
                          'ob_komments', 'ob_sets01', 'ob_sets02', 'ob_sets03', 'ob_sets04', 'ob_sets05']
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get object by folder {modelfolder}: {e}")
            return None
    
    def add_object(self, object_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Add a new object to the database."""
        try:
            # Validate required fields
            if not object_data.get('first_name') or not object_data.get('last_name'):
                return False, "First name and last name are required"
            
            # Validate name format
            if not self._validate_name(object_data['first_name']):
                return False, "Invalid first name format"
            
            if not self._validate_name(object_data['last_name']):
                return False, "Invalid last name format"
            
            # Validate comments length
            if object_data.get('ob_komments') and len(object_data['ob_komments']) > 500:
                return False, "Comments too long (max 500 characters)"
            
            # Generate model folder name
            modelfolder = self._generate_model_folder(
                object_data['first_name'], 
                object_data['category']
            )
            
            # Check for duplicates
            if self.get_object_by_folder(modelfolder):
                return False, "Object with this name already exists"
            
            # Set default values
            object_data['modelfolder'] = modelfolder
            object_data['foto'] = self._get_avatar_for_category(object_data.get('category', '4'))
            
            # Set default values for optional fields
            for field in ['homenumb', 'apartmentnumb', 'floornumb', 'phone']:
                if not object_data.get(field):
                    object_data[field] = "0"
            
            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO People (
                last_name, first_name, phone, category, homenumb, 
                apartmentnumb, floornumb, modelfolder, foto, userlink, ob_komments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                object_data['last_name'],
                object_data['first_name'],
                object_data['phone'],
                object_data['category'],
                object_data['homenumb'],
                object_data['apartmentnumb'],
                object_data['floornumb'],
                object_data['modelfolder'],
                object_data['foto'],
                object_data.get('userlink', ''),
                object_data.get('ob_komments', '')
            ))
            
            conn.commit()
            conn.close()
            
            # Create dataset folder
            self._create_dataset_folder(modelfolder)
            
            logger.info(f"Added new object: {object_data['first_name']} {object_data['last_name']}")
            return True, f"Object added successfully. Model folder: {modelfolder}"
            
        except Exception as e:
            logger.error(f"Failed to add object: {e}")
            return False, f"Database error: {e}"
    
    def update_object(self, modelfolder: str, object_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an existing object."""
        try:
            # Cannot update Unknown object
            if modelfolder == 'Unknown':
                return False, "Cannot update Unknown object"
            
            # Validate required fields
            if not object_data.get('first_name') or not object_data.get('last_name'):
                return False, "First name and last name are required"
            
            # Validate name format
            if not self._validate_name(object_data['first_name']):
                return False, "Invalid first name format"
            
            if not self._validate_name(object_data['last_name']):
                return False, "Invalid last name format"
            
            # Validate comments length
            if object_data.get('ob_komments') and len(object_data['ob_komments']) > 500:
                return False, "Comments too long (max 500 characters)"
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE People SET 
                last_name = ?, first_name = ?, phone = ?, category = ?, 
                homenumb = ?, apartmentnumb = ?, floornumb = ?, foto = ?, 
                userlink = ?, ob_komments = ?
            WHERE modelfolder = ?
            ''', (
                object_data['last_name'],
                object_data['first_name'],
                object_data['phone'],
                object_data['category'],
                object_data['homenumb'],
                object_data['apartmentnumb'],
                object_data['floornumb'],
                object_data['foto'],
                object_data.get('userlink', ''),
                object_data.get('ob_komments', ''),
                modelfolder
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated object: {modelfolder}")
            return True, "Object updated successfully"
            
        except Exception as e:
            logger.error(f"Failed to update object {modelfolder}: {e}")
            return False, f"Database error: {e}"
    
    def delete_object(self, modelfolder: str) -> Tuple[bool, str]:
        """Delete an object from the database."""
        try:
            # Cannot delete Unknown object
            if modelfolder == 'Unknown':
                return False, "Cannot delete Unknown object"
            
            # Get object info before deletion
            obj = self.get_object_by_folder(modelfolder)
            if not obj:
                return False, "Object not found"
            
            # Delete from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM People WHERE modelfolder = ?', (modelfolder,))
            
            conn.commit()
            conn.close()
            
            # Optionally remove dataset folder (ask user in UI)
            # self._remove_dataset_folder(modelfolder)
            
            logger.info(f"Deleted object: {modelfolder}")
            return True, f"Object '{obj['first_name']} {obj['last_name']}' deleted successfully"
            
        except Exception as e:
            logger.error(f"Failed to delete object {modelfolder}: {e}")
            return False, f"Database error: {e}"
    
    def _validate_name(self, name: str) -> bool:
        """Validate name format (Russian/English letters only, max 20 chars)."""
        if not name or len(name) > 20:
            return False
        return bool(re.match(r'^[а-яА-ЯёЁa-zA-Z0-9]+$', name.strip()))
    
    def _generate_model_folder(self, first_name: str, category: str) -> str:
        """Generate unique model folder name."""
        # Get next number from registry
        registry_path = os.path.join(os.path.dirname(self.db_path), '..', 'numberreestr.txt')
        
        try:
            if os.path.exists(registry_path):
                with open(registry_path, 'r') as f:
                    number = int(f.read().strip()) + 1
            else:
                number = 10000
            
            with open(registry_path, 'w') as f:
                f.write(str(number))
        except:
            number = 10000
        
        # Transliterate first name
        transliterated = ''.join(
            translit(char, "ru", "en") if 'а' <= char <= 'я' or 'А' <= char <= 'Я' else char
            for char in first_name.strip()
        )
        
        return f"{number}_{category}_{transliterated}"
    
    def _get_avatar_for_category(self, category: str) -> str:
        """Get avatar filename based on category."""
        avatars = {
            '1': 'no_avatar_green.jpg',
            '2': 'no_avatar_grey.jpg',
            '3': 'no_avatar_blue.jpg',
            '4': 'no_avatar_red.jpg'
        }
        return avatars.get(category, 'no_avatar_grey.jpg')
    
    def _create_dataset_folder(self, modelfolder: str) -> None:
        """Create dataset folder for training."""
        dataset_path = os.path.join(os.path.dirname(self.db_path), '..', 'dataset', modelfolder)
        try:
            os.makedirs(dataset_path, exist_ok=True)
            logger.info(f"Created dataset folder: {dataset_path}")
        except Exception as e:
            logger.error(f"Failed to create dataset folder {dataset_path}: {e}")
    
    def _remove_dataset_folder(self, modelfolder: str) -> None:
        """Remove dataset folder (optional)."""
        dataset_path = os.path.join(os.path.dirname(self.db_path), '..', 'dataset', modelfolder)
        try:
            if os.path.exists(dataset_path):
                import shutil
                shutil.rmtree(dataset_path)
                logger.info(f"Removed dataset folder: {dataset_path}")
        except Exception as e:
            logger.error(f"Failed to remove dataset folder {dataset_path}: {e}")


# Global instance
objects_manager = ObjectsManager()

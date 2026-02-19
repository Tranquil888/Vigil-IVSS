"""
Configuration management for Vigil surveillance system.
"""

import os
import sqlite3
from typing import Dict, Any, Optional
from vigil.config.constants import SETTING_DB_PATH, LOG_FILE, LOG_FORMAT


class SettingsManager:
    """Manages application settings with database persistence."""
    
    def __init__(self, db_path: str = SETTING_DB_PATH):
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self) -> None:
        """Create database and default settings if they don't exist."""
        if not os.path.isfile(self.db_path):
            self._create_database()
    
    def _create_database(self) -> None:
        """Create the settings database with default values."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS setting (
                    parametr_name TEXT,
                    set01 TEXT,
                    set02 TEXT,
                    set03 TEXT,
                    set04 TEXT,
                    set05 TEXT,
                    set06 TEXT,
                    set07 TEXT,
                    set08 TEXT,
                    set09 TEXT,
                    set10 TEXT
                )
            ''')
            
            # Insert default settings
            defaults = [
                ('model_forone', '0', '0', '0', '0', None, None, None, None, None, None),  # время на одну. объектов. файлов. размер
                ('numberreestr', '10000', None, None, None, None, None, None, None, None, None),
                ('model_algorithm', 'cnn', None, None, None, None, None, None, None, None, None),  # Face detection algorithm
                ('recognition_tolerance', '0.6', None, None, None, None, None, None, None, None, None),  # Face recognition tolerance
                ('objects_pic', 'circle', None, None, None, None, None, None, None, None, None),
                ('enabled_sec', '1', None, None, None, None, None, None, None, None, None),
                ('stream', '127.0.0.1', '8000', None, None, None, None, None, None, None, None),
                ('stream_res_qua', '704', '90', None, None, None, None, None, None, None, None),  # разрешение. качество
                ('resolut_video_model', '60', None, None, None, None, None, None, None, None, None),  # резрешение для модели
                ('facerecog_granici1_face', '2', '4', '6', None, None, None, None, None, None, None),
                ('video_save', '10', 'XVID', '15', None, None, None, None, None, None, None),  # продолжит. кодек. кадров
                ('foto_save', '10', None, None, None, None, None, None, None, None, None),  # сохранение кадров для известных
                ('oper_jurnal', '5', '60', None, None, None, None, None, None, None, None),  # групировка строк в оперативном журнале
                ('time_format', '1', None, None, None, None, None, None, None, None, None),  # формат времени
                # Training-related settings
                ('base_path', os.getcwd(), None, None, None, None, None, None, None, None, None),  # Base application path
                ('dataset_path', os.path.join(os.getcwd(), 'data', 'dataset'), None, None, None, None, None, None, None, None, None),  # Training dataset path
                ('model_path', os.path.join(os.getcwd(), 'data', 'encodings.pickle'), None, None, None, None, None, None, None, None, None),  # Model file path
                ('archive_path', os.path.join(os.getcwd(), 'data', 'data_archives', 'dataset_archives'), None, None, None, None, None, None, None, None, None),  # Archive path
                ('auto_retrain', '0', None, None, None, None, None, None, None, None, None),  # Auto retrain on dataset changes
                ('min_images_per_person', '5', None, None, None, None, None, None, None, None, None),  # Minimum images required per person
                # Face recognition runtime settings
                ('face_recognition_enabled', '1', None, None, None, None, None, None, None, None, None),  # Enable/disable face recognition
                ('recognition_confidence_threshold', '0.6', None, None, None, None, None, None, None, None, None),  # Recognition tolerance (0.1=strict, 0.8=lenient)
                ('recognition_frame_skip', '3', None, None, None, None, None, None, None, None, None),  # Process every Nth frame for recognition
                ('recognition_cooldown', '2', None, None, None, None, None, None, None, None, None),  # Seconds between recognition events for same person
                ('show_unknown_faces', '1', None, None, None, None, None, None, None, None, None),  # Show unknown face alerts
                ('recognition_roi_enabled', '0', None, None, None, None, None, None, None, None, None),  # Enable region of interest for recognition
            ]
            
            for default in defaults:
                placeholders = ','.join(['?'] * len(default))
                cursor.execute(f'INSERT INTO setting VALUES ({placeholders})', default)
            
            connection.commit()
            connection.close()
            
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to create settings database: {e}")
    
    def get_setting(self, parameter_name: str, default: Any = None) -> Any:
        """Get a setting value by parameter name."""
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            cursor.execute('SELECT set01, set02, set03, set04, set05 FROM setting WHERE parametr_name = ?', (parameter_name,))
            result = cursor.fetchone()
            connection.close()
            
            if result:
                # Return first non-None value
                for value in result:
                    if value is not None:
                        return value
            return default
            
        except sqlite3.Error as e:
            print(f"Error getting setting {parameter_name}: {e}")
            return default
    
    def set_setting(self, parameter_name: str, *values) -> None:
        """Set a setting value."""
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            # Check if setting exists
            cursor.execute('SELECT parametr_name FROM setting WHERE parametr_name = ?', (parameter_name,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing setting
                placeholders = ','.join([f'set{i+1} = ?' for i in range(len(values))])
                cursor.execute(f'UPDATE setting SET {placeholders} WHERE parametr_name = ?', values + (parameter_name,))
            else:
                # Insert new setting
                all_values = (parameter_name,) + values + (None,) * (10 - len(values) - 1)
                placeholders = ','.join(['?'] * len(all_values))
                cursor.execute(f'INSERT INTO setting VALUES ({placeholders})', all_values)
            
            connection.commit()
            connection.close()
            
        except sqlite3.Error as e:
            print(f"Error setting setting {parameter_name}: {e}")
    
    def get_all_settings(self) -> Dict[str, Dict[str, str]]:
        """Get all settings as a dictionary."""
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            cursor.execute('SELECT * FROM setting')
            rows = cursor.fetchall()
            connection.close()
            
            settings = {}
            for row in rows:
                param_name = row[0]
                settings[param_name] = {
                    'set01': row[1],
                    'set02': row[2],
                    'set03': row[3],
                    'set04': row[4],
                    'set05': row[5],
                    'set06': row[6],
                    'set07': row[7],
                    'set08': row[8],
                    'set09': row[9],
                    'set10': row[10],
                }
            
            return settings
            
        except sqlite3.Error as e:
            print(f"Error getting all settings: {e}")
            return {}


# Global settings instance
settings = SettingsManager()

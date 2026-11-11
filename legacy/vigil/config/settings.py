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
            
            defaults = [
                ('model_forone', '0', '0', '0', '0', None, None, None, None, None, None),
                ('numberreestr', '10000', None, None, None, None, None, None, None, None, None),
                ('model_algorithm', 'cnn', None, None, None, None, None, None, None, None, None),
                ('recognition_tolerance', '0.6', None, None, None, None, None, None, None, None, None),
                ('objects_pic', 'circle', None, None, None, None, None, None, None, None, None),
                ('enabled_sec', '1', None, None, None, None, None, None, None, None, None),
                ('stream', '127.0.0.1', '8000', None, None, None, None, None, None, None, None),
                ('stream_res_qua', '704', '90', None, None, None, None, None, None, None, None),
                ('resolut_video_model', '60', None, None, None, None, None, None, None, None, None),
                ('facerecog_granici1_face', '2', '4', '6', None, None, None, None, None, None, None),
                ('video_save', '10', 'XVID', '15', None, None, None, None, None, None, None),
                ('foto_save', '10', None, None, None, None, None, None, None, None, None),
                ('oper_jurnal', '5', '60', None, None, None, None, None, None, None, None),
                ('time_format', '1', None, None, None, None, None, None, None, None, None),
                # Training-related settings
                ('base_path', os.getcwd(), None, None, None, None, None, None, None, None, None),
                ('dataset_path', os.path.join(os.getcwd(), 'data', 'dataset'), None, None, None, None, None, None, None, None, None),
                ('model_path', os.path.join(os.getcwd(), 'data', 'encodings.pickle'), None, None, None, None, None, None, None, None, None),
                ('archive_path', os.path.join(os.getcwd(), 'data', 'data_archives', 'dataset_archives'), None, None, None, None, None, None, None, None, None),
                ('auto_retrain', '0', None, None, None, None, None, None, None, None, None),
                ('min_images_per_person', '5', None, None, None, None, None, None, None, None, None),
                # Face recognition runtime settings
                ('face_recognition_enabled', '1', None, None, None, None, None, None, None, None, None),
                ('recognition_confidence_threshold', '0.6', None, None, None, None, None, None, None, None, None),  # Recognition tolerance (0.1=strict, 0.8=lenient)
                ('recognition_frame_skip', '3', None, None, None, None, None, None, None, None, None),
                ('recognition_cooldown', '2', None, None, None, None, None, None, None, None, None),
                ('show_unknown_faces', '1', None, None, None, None, None, None, None, None, None),
                ('camera_max_fps', '30', None, None, None, None, None, None, None, None, None),
                ('recognition_roi_enabled', '0', None, None, None, None, None, None, None, None, None),
                # Video analysis settings
                ('video_loop_playback', '0', None, None, None, None, None, None, None, None, None),
                ('video_progress_show', '1', None, None, None, None, None, None, None, None, None),
                ('video_playback_speed', '1.0', None, None, None, None, None, None, None, None, None),
                # Event journal settings
                ('event_inactivity_delay', '10', None, None, None, None, None, None, None, None, None),
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
            
            cursor.execute('SELECT parametr_name FROM setting WHERE parametr_name = ?', (parameter_name,))
            exists = cursor.fetchone()
            
            if exists:
                placeholders = ','.join([f'set{i+1:02d} = ?' for i in range(len(values))])
                cursor.execute(f'UPDATE setting SET {placeholders} WHERE parametr_name = ?', values + (parameter_name,))
            else:
                # Database has 11 columns: parametr_name + set01-set10
                total_columns = 11
                current_values = (parameter_name,) + values
                padding_needed = total_columns - len(current_values)
                all_values = current_values + (None,) * padding_needed
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


settings = SettingsManager()

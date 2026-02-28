"""
Database management for Vigil surveillance system.
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional, Tuple
from vigil.core.exceptions import DatabaseError
from vigil.utils.logging_config import get_database_logger
from vigil.config.constants import (
    SETTING_DB_PATH, AUTH_DB_PATH, OBJECTS_DB_PATH, CAMERA_DB_PATH, EVENTS_DB_PATH
)


class DatabaseManager:
    """Manages database connections and operations for Vigil system."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = get_database_logger()
        self._ensure_database_exists()
    
    def _ensure_database_exists(self) -> None:
        """Create database directory and file if they don't exist."""
        if not os.path.isfile(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        try:
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            return connection
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database {self.db_path}: {e}")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a SELECT query and return results."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Query execution failed: {query}, params: {params}, error: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            self.logger.error(f"Update execution failed: {query}, params: {params}, error: {e}")
            raise DatabaseError(f"Update execution failed: {e}")
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute a query multiple times with different parameters."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            self.logger.error(f"Batch execution failed: {query}, error: {e}")
            raise DatabaseError(f"Batch execution failed: {e}")


class SettingsDatabase(DatabaseManager):
    """Manages application settings database."""
    
    def __init__(self):
        super().__init__(SETTING_DB_PATH)
        self._create_tables()
        self._insert_defaults()
    
    def _create_tables(self) -> None:
        """Create settings table if it doesn't exist."""
        query = '''
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
        '''
        self.execute_update(query)
    
    def _insert_defaults(self) -> None:
        """Insert default settings if table is empty."""
        existing = self.execute_query("SELECT COUNT(*) as count FROM setting")
        if existing[0]['count'] > 0:
            return
        
        defaults = [
            ('model_forone', '0', '0', '0', '0'),
            ('numberreestr', '10000'),
            ('model_algoritm', 'cnn'),
            ('objects_pic', 'circle'),
            ('enabled_sec', '1'),
            ('stream', '127.0.0.1', '8000'),
            ('stream_res_qua', '704', '90'),
            ('resolut_video_model', '60'),
            ('facerecog_granici1_face', '2', '4', '6'),
            ('video_save', '10', 'XVID', '15'),
            ('foto_save', '10'),
            ('oper_jurnal', '5', '60'),
            ('time_format', '1'),
        ]
        
        for default in defaults:
            placeholders = ','.join(['?'] * len(default))
            query = f'INSERT INTO setting VALUES ({placeholders})'
            self.execute_update(query, default)
    
    def get_setting(self, parameter_name: str, default: Any = None) -> Any:
        """Get a setting value."""
        query = 'SELECT set01, set02, set03, set04, set05 FROM setting WHERE parametr_name = ?'
        results = self.execute_query(query, (parameter_name,))
        
        if results:
            row = results[0]
            for value in row:
                if value is not None:
                    return value
        return default
    
    def set_setting(self, parameter_name: str, *values) -> None:
        """Set a setting value."""
        # Check if setting exists
        existing = self.execute_query('SELECT parametr_name FROM setting WHERE parametr_name = ?', (parameter_name,))
        
        if existing:
            # Update existing setting
            placeholders = ','.join([f'set{i+1} = ?' for i in range(len(values))])
            query = f'UPDATE setting SET {placeholders} WHERE parametr_name = ?'
            self.execute_update(query, values + (parameter_name,))
        else:
            # Insert new setting
            all_values = (parameter_name,) + values + (None,) * (10 - len(values) - 1)
            placeholders = ','.join(['?'] * len(all_values))
            query = f'INSERT INTO setting VALUES ({placeholders})'
            self.execute_update(query, all_values)


class AuthenticationDatabase(DatabaseManager):
    """Manages user authentication database."""
    
    def __init__(self):
        super().__init__(AUTH_DB_PATH)
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create authentication tables."""
        users_query = '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                login_attempts INTEGER DEFAULT 0
            )
        '''
        self.execute_update(users_query)
    
    def create_user(self, username: str, password_hash: str, role: str) -> bool:
        """Create a new user."""
        try:
            query = 'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)'
            self.execute_update(query, (username, password_hash, role))
            return True
        except DatabaseError:
            return False
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information by username."""
        query = 'SELECT * FROM users WHERE username = ?'
        results = self.execute_query(query, (username,))
        
        if results:
            return dict(results[0])
        return None
    
    def update_login_attempt(self, username: str, attempts: int) -> None:
        """Update login attempts for a user."""
        query = 'UPDATE users SET login_attempts = ? WHERE username = ?'
        self.execute_update(query, (attempts, username))
    
    def update_last_login(self, username: str) -> None:
        """Update last login timestamp for a user."""
        query = 'UPDATE users SET last_login = CURRENT_TIMESTAMP, login_attempts = 0 WHERE username = ?'
        self.execute_update(query, (username,))
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        query = 'SELECT id, username, role, created_at, last_login FROM users ORDER BY username'
        results = self.execute_query(query)
        return [dict(row) for row in results]
    
    def delete_user(self, username: str) -> bool:
        """Delete a user."""
        try:
            query = 'DELETE FROM users WHERE username = ?'
            affected = self.execute_update(query, (username,))
            return affected > 0
        except DatabaseError:
            return False


class ObjectsDatabase(DatabaseManager):
    """Manages objects/people database for recognition."""
    
    def __init__(self):
        super().__init__(OBJECTS_DB_PATH)
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create objects tables."""
        objects_query = '''
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                family TEXT,
                category TEXT,
                home_number TEXT,
                apartment_number TEXT,
                floor_number TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
        self.execute_update(objects_query)
    
    def create_object(self, name: str, **kwargs) -> int:
        """Create a new object record."""
        fields = ['name'] + list(kwargs.keys())
        placeholders = ','.join(['?'] * len(fields))
        values = [name] + list(kwargs.values())
        
        query = f'INSERT INTO objects ({",".join(fields)}) VALUES ({placeholders})'
        self.execute_update(query, tuple(values))
        
        # Get the ID of the inserted record
        result = self.execute_query('SELECT last_insert_rowid()')
        return result[0]['last_insert_rowid()']
    
    def get_object(self, object_id: int) -> Optional[Dict[str, Any]]:
        """Get object by ID."""
        query = 'SELECT * FROM objects WHERE id = ?'
        results = self.execute_query(query, (object_id,))
        
        if results:
            return dict(results[0])
        return None
    
    def get_all_objects(self) -> List[Dict[str, Any]]:
        """Get all objects."""
        query = 'SELECT * FROM objects ORDER BY name'
        results = self.execute_query(query)
        return [dict(row) for row in results]
    
    def update_object(self, object_id: int, **kwargs) -> bool:
        """Update object information."""
        if not kwargs:
            return False
        
        set_clause = ','.join([f'{key} = ?' for key in kwargs.keys()])
        values = list(kwargs.values()) + [object_id]
        
        query = f'UPDATE objects SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
        affected = self.execute_update(query, tuple(values))
        return affected > 0
    
    def delete_object(self, object_id: int) -> bool:
        """Delete an object."""
        query = 'DELETE FROM objects WHERE id = ?'
        affected = self.execute_update(query, (object_id,))
        return affected > 0


class CameraDatabase(DatabaseManager):
    """Manages camera settings database."""
    
    def __init__(self):
        super().__init__(CAMERA_DB_PATH)
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create camera tables."""
        cameras_query = '''
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activ_number TEXT UNIQUE NOT NULL,
                name TEXT,
                link TEXT,
                source_type TEXT DEFAULT 'camera',
                cam_set_a TEXT,
                cam_set_b TEXT,
                cam_set_c TEXT,
                cam_set_d TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
        self.execute_update(cameras_query)
        self._migrate_database()
    
    def _migrate_database(self) -> None:
        """Migrate existing database to new schema."""
        try:
            # Check if name column exists
            result = self.execute_query("PRAGMA table_info(cameras)")
            columns = [row['name'] for row in result]
            
            if 'name' not in columns:
                self.execute_update("ALTER TABLE cameras ADD COLUMN name TEXT")
                self.logger.info("Added name column to cameras table")
            
            if 'source_type' not in columns:
                self.execute_update("ALTER TABLE cameras ADD COLUMN source_type TEXT DEFAULT 'camera'")
                self.logger.info("Added source_type column to cameras table")
                
        except Exception as e:
            self.logger.warning(f"Database migration failed (may already be migrated): {e}")
    
    def create_camera(self, activ_number: str, link: str = None, source_type: str = 'camera', name: str = None, **settings) -> int:
        """Create a new camera record."""
        # Build fields and values dynamically
        fields = ['activ_number']
        values = [activ_number]
        
        if name is not None:
            fields.append('name')
            values.append(name)
        
        if link is not None:
            fields.append('link')
            values.append(link)
            
        fields.append('source_type')
        values.append(source_type)
        
        # Add any additional settings
        for key, value in settings.items():
            if key.startswith('cam_set_'):
                fields.append(key)
                values.append(value)
        
        placeholders = ','.join(['?'] * len(fields))
        query = f'INSERT INTO cameras ({",".join(fields)}) VALUES ({placeholders})'
        self.execute_update(query, tuple(values))
        
        result = self.execute_query('SELECT last_insert_rowid()')
        return result[0]['last_insert_rowid()']
    
    def get_camera(self, activ_number: str) -> Optional[Dict[str, Any]]:
        """Get camera by activation number."""
        query = 'SELECT * FROM cameras WHERE activ_number = ?'
        results = self.execute_query(query, (activ_number,))
        
        if results:
            return dict(results[0])
        return None
    
    def get_all_cameras(self) -> List[Dict[str, Any]]:
        """Get all cameras."""
        query = 'SELECT * FROM cameras ORDER BY activ_number'
        results = self.execute_query(query)
        return [dict(row) for row in results]
    
    def update_camera(self, activ_number: str, **kwargs) -> bool:
        """Update camera settings."""
        if not kwargs:
            return False
        
        set_clause = ','.join([f'{key} = ?' for key in kwargs.keys()])
        values = list(kwargs.values()) + [activ_number]
        
        query = f'UPDATE cameras SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE activ_number = ?'
        affected = self.execute_update(query, tuple(values))
        return affected > 0
    
    def delete_camera(self, activ_number: str) -> bool:
        """Delete a camera."""
        query = 'DELETE FROM cameras WHERE activ_number = ?'
        affected = self.execute_update(query, (activ_number,))
        return affected > 0


class EventSessionsDatabase(DatabaseManager):
    """Manages event sessions and photos database for journal functionality."""
    
    def __init__(self):
        super().__init__(os.path.join(os.getcwd(), 'data/events.db'))
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create event sessions and photos tables."""
        # Event sessions table
        sessions_query = '''
            CREATE TABLE IF NOT EXISTS event_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration INTEGER,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
        self.execute_update(sessions_query)
        
        # Event photos table
        photos_query = '''
            CREATE TABLE IF NOT EXISTS event_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                object_name TEXT,
                photo_path TEXT,
                timestamp TEXT,
                confidence REAL,
                FOREIGN KEY (event_id) REFERENCES event_sessions (id)
            )
        '''
        self.execute_update(photos_query)
        
        # Event objects table for tracking objects in sessions
        objects_query = '''
            CREATE TABLE IF NOT EXISTS event_objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                object_name TEXT,
                object_type TEXT,
                confidence REAL,
                timestamp TEXT,
                FOREIGN KEY (event_id) REFERENCES event_sessions (id)
            )
        '''
        self.execute_update(objects_query)
        
        # Event videos table for storing video clips
        videos_query = '''
            CREATE TABLE IF NOT EXISTS event_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                video_path TEXT,
                start_time TEXT,
                end_time TEXT,
                duration INTEGER,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES event_sessions (id)
            )
        '''
        self.execute_update(videos_query)
        
        # Create indexes for better performance
        self.execute_update('CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON event_sessions(start_time)')
        self.execute_update('CREATE INDEX IF NOT EXISTS idx_photos_event_id ON event_photos(event_id)')
        self.execute_update('CREATE INDEX IF NOT EXISTS idx_objects_event_id ON event_objects(event_id)')
        self.execute_update('CREATE INDEX IF NOT EXISTS idx_videos_event_id ON event_videos(event_id)')
    
    def create_event_session(self, start_time: str, description: str = None) -> int:
        """Create a new event session."""
        query = 'INSERT INTO event_sessions (start_time, description) VALUES (?, ?)'
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (start_time, description))
                conn.commit()
                
                # Get the last insert rowid from the same connection
                cursor.execute('SELECT last_insert_rowid()')
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    return 0
                    
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create event session: {e}")
            return 0
    
    def end_event_session(self, session_id: int, end_time: str, duration: int) -> bool:
        """End an event session."""
        query = 'UPDATE event_sessions SET end_time = ?, duration = ? WHERE id = ?'
        affected = self.execute_update(query, (end_time, duration, session_id))
        return affected > 0
    
    def add_event_photo(self, event_id: int, object_name: str, photo_path: str, 
                       timestamp: str, confidence: float) -> int:
        """Add a photo to an event session."""
        query = '''
            INSERT INTO event_photos (event_id, object_name, photo_path, timestamp, confidence)
            VALUES (?, ?, ?, ?, ?)
        '''
        self.execute_update(query, (event_id, object_name, photo_path, timestamp, confidence))
        
        result = self.execute_query('SELECT last_insert_rowid()')
        return result[0]['last_insert_rowid()']
    
    def add_event_object(self, event_id: int, object_name: str, object_type: str, 
                        timestamp: str, confidence: float) -> int:
        """Add an object recognition to an event session."""
        query = '''
            INSERT INTO event_objects (event_id, object_name, object_type, timestamp, confidence)
            VALUES (?, ?, ?, ?, ?)
        '''
        self.execute_update(query, (event_id, object_name, object_type, timestamp, confidence))
        
        result = self.execute_query('SELECT last_insert_rowid()')
        return result[0]['last_insert_rowid()']
    
    def get_event_sessions(self, limit: int = 100, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get event sessions with optional date filtering."""
        query = '''
            SELECT id, start_time, end_time, duration, description, created_at
            FROM event_sessions
        '''
        params = []
        
        # Add date filtering if provided
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append("DATE(start_time) >= DATE(?)")
                params.append(start_date)
            if end_date:
                conditions.append("DATE(start_time) <= DATE(?)")
                params.append(end_date)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        query += '''
            ORDER BY start_time DESC
            LIMIT ?
        '''
        params.append(limit)
        
        results = self.execute_query(query, tuple(params))
        return [dict(row) for row in results]
    
    def get_event_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific event session."""
        query = 'SELECT * FROM event_sessions WHERE id = ?'
        results = self.execute_query(query, (session_id,))
        
        if results:
            return dict(results[0])
        return None
    
    def get_event_photos(self, session_id: int, object_name: str = None) -> List[Dict[str, Any]]:
        """Get photos for an event session with optional object name filtering."""
        query = '''
            SELECT id, object_name, photo_path, timestamp, confidence
            FROM event_photos
            WHERE event_id = ?
        '''
        params = [session_id]
        
        # Add object name filter if provided
        if object_name:
            query += ' AND object_name LIKE ?'
            params.append(f'%{object_name}%')
        
        query += ' ORDER BY timestamp'
        
        results = self.execute_query(query, tuple(params))
        return [dict(row) for row in results]
    
    def get_event_objects(self, session_id: int, object_name: str = None, object_type: str = None) -> List[Dict[str, Any]]:
        """Get objects recognized in an event session with optional filtering."""
        query = '''
            SELECT id, object_name, object_type, timestamp, confidence
            FROM event_objects
            WHERE event_id = ?
        '''
        params = [session_id]
        
        # Add object name filter if provided
        if object_name:
            query += ' AND object_name LIKE ?'
            params.append(f'%{object_name}%')
        
        # Add object type filter if provided
        if object_type:
            query += ' AND object_type LIKE ?'
            params.append(f'%{object_type}%')
        
        query += ' ORDER BY timestamp'
        
        results = self.execute_query(query, tuple(params))
        return [dict(row) for row in results]
    
    def get_all_recognized_objects(self, object_name: str = None, object_type: str = None, 
                                 limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all recognized objects across all events with optional filtering."""
        try:
            query = '''
                SELECT eo.id, eo.event_id, eo.object_name, eo.object_type, 
                       eo.timestamp, eo.confidence, es.start_time as event_start_time,
                       es.description as event_description
                FROM event_objects eo
                JOIN event_sessions es ON eo.event_id = es.id
                WHERE 1=1
            '''
            params = []
            
            # Add object name filter if provided
            if object_name:
                query += ' AND eo.object_name LIKE ?'
                params.append(f'%{object_name}%')
            
            # Add object type filter if provided
            if object_type:
                query += ' AND eo.object_type LIKE ?'
                params.append(f'%{object_type}%')
            
            # Add ordering and pagination
            query += ' ORDER BY eo.timestamp DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            results = self.execute_query(query, tuple(params))
            return [dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"Error getting all recognized objects: {e}")
            return []
    
    def add_event_video(self, event_id: int, video_path: str, start_time: str, 
                       end_time: str, duration: int, file_size: int) -> int:
        """Add a video clip to an event session."""
        query = '''
            INSERT INTO event_videos (event_id, video_path, start_time, end_time, duration, file_size)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (event_id, video_path, start_time, end_time, duration, file_size))
                conn.commit()
                
                # Get the last insert rowid from the same connection
                cursor.execute('SELECT last_insert_rowid()')
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    return 0
                    
        except sqlite3.Error as e:
            self.logger.error(f"Failed to add event video: {e}")
            return 0
    
    def get_event_videos(self, session_id: int) -> List[Dict[str, Any]]:
        """Get videos for an event session."""
        query = '''
            SELECT id, video_path, start_time, end_time, duration, file_size, created_at
            FROM event_videos
            WHERE event_id = ?
            ORDER BY created_at
        '''
        results = self.execute_query(query, (session_id,))
        return [dict(row) for row in results]
    
    def get_all_photos(self, date_from: str = None, date_to: str = None, 
                    object_name: str = None, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all photos with optional filtering.
        
        Args:
            date_from: Start date filter (YYYY-MM-DD format)
            date_to: End date filter (YYYY-MM-DD format)
            object_name: Object name filter (partial match)
            limit: Maximum number of photos to return
            offset: Number of photos to skip
            
        Returns:
            List of photo records
        """
        try:
            # Build query with filters
            query = '''
                SELECT ep.id, ep.event_id, ep.object_name, ep.photo_path, 
                       ep.timestamp, ep.confidence,
                       es.start_time, es.description
                FROM event_photos ep
                JOIN event_sessions es ON ep.event_id = es.id
                WHERE 1=1
            '''
            params = []
            
            # Add date filters
            if date_from:
                query += ' AND DATE(es.start_time) >= DATE(?)'
                params.append(date_from)
            
            if date_to:
                query += ' AND DATE(es.start_time) <= DATE(?)'
                params.append(date_to)
            
            # Add object filter
            if object_name:
                query += ' AND ep.object_name LIKE ?'
                params.append(f'%{object_name}%')
            
            # Add ordering and pagination
            query += ' ORDER BY ep.timestamp DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            results = self.execute_query(query, tuple(params))
            return [dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"Error getting all photos: {e}")
            return []
    
    def get_available_dates(self) -> List[str]:
        """
        Get list of available dates for filtering.
        
        Returns:
            List of date strings in YYYY-MM-DD format, sorted descending
        """
        try:
            query = '''
                SELECT DISTINCT DATE(es.start_time) as date
                FROM event_sessions es
                JOIN event_photos ep ON es.id = ep.event_id
                ORDER BY date DESC
            '''
            results = self.execute_query(query)
            dates = [row[0] for row in results]
            return dates
            
        except Exception as e:
            self.logger.error(f"Error getting available dates: {e}")
            return []
    
    def get_available_event_dates(self) -> List[str]:
        """
        Get list of available event dates for filtering.
        
        Returns:
            List of date strings in YYYY-MM-DD format, sorted descending
        """
        try:
            query = '''
                SELECT DISTINCT DATE(start_time) as date
                FROM event_sessions
                ORDER BY date DESC
            '''
            results = self.execute_query(query)
            dates = [row[0] for row in results]
            return dates
            
        except Exception as e:
            self.logger.error(f"Error getting available event dates: {e}")
            return []
    
    def delete_photos(self, photo_ids: List[int]) -> bool:
        """
        Delete specific photos by their IDs.
        
        Args:
            photo_ids: List of photo IDs to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not photo_ids:
                return False
            
            # Build placeholders for IN clause
            placeholders = ','.join(['?' for _ in photo_ids])
            
            query = f'DELETE FROM event_photos WHERE id IN ({placeholders})'
            affected = self.execute_update(query, tuple(photo_ids))
            
            self.logger.info(f"Deleted {len(photo_ids)} photos from database")
            return affected > 0
            
        except Exception as e:
            self.logger.error(f"Error deleting photos: {e}")
            return False
    
    def delete_event_session(self, session_id: int) -> bool:
        """Delete an event session and all related photos, objects, and videos."""
        try:
            # Delete related photos, objects, and videos first
            self.execute_update('DELETE FROM event_photos WHERE event_id = ?', (session_id,))
            self.execute_update('DELETE FROM event_objects WHERE event_id = ?', (session_id,))
            self.execute_update('DELETE FROM event_videos WHERE event_id = ?', (session_id,))
            
            # Delete the session
            query = 'DELETE FROM event_sessions WHERE id = ?'
            affected = self.execute_update(query, (session_id,))
            return affected > 0
        except Exception:
            return False


# Database factory functions
def get_settings_db() -> SettingsDatabase:
    """Get settings database instance."""
    return SettingsDatabase()

def get_auth_db() -> AuthenticationDatabase:
    """Get authentication database instance."""
    return AuthenticationDatabase()

def get_objects_db() -> ObjectsDatabase:
    """Get objects database instance."""
    return ObjectsDatabase()

def get_camera_db() -> CameraDatabase:
    """Get camera database instance."""
    return CameraDatabase()

def get_events_db() -> EventSessionsDatabase:
    """Get event sessions database instance."""
    return EventSessionsDatabase()

"""
Event logging module for Vigil surveillance system.
"""

import sqlite3
import datetime
import os
from typing import List, Dict, Any, Optional
from vigil.core.exceptions import DatabaseError
from vigil.utils.logging_config import get_events_logger
from vigil.config.constants import OBJECTS_DB_PATH


class EventLogger:
    """Logs and manages surveillance events."""
    
    def __init__(self):
        self.logger = get_events_logger()
        self.db_path = os.path.join(os.getcwd(), 'data/events.db')
        self._ensure_database_exists()
    
    def _ensure_database_exists(self) -> None:
        """Create events database if it doesn't exist."""
        if not os.path.isfile(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._create_database()
    
    def _create_database(self) -> None:
        """Create the events database and tables."""
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    object_name TEXT,
                    confidence REAL,
                    camera_source TEXT,
                    frame_path TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_object_name ON events(object_name)')
            
            connection.commit()
            connection.close()
            
            self.logger.info("Events database created successfully")
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create events database: {e}")
            raise DatabaseError(f"Failed to create events database: {e}")
    
    def log_event(self, event_type: str, object_name: Optional[str] = None,
                  confidence: Optional[float] = None, camera_source: Optional[str] = None,
                  frame_path: Optional[str] = None, description: Optional[str] = None) -> bool:
        """
        Log a surveillance event.
        
        Args:
            event_type: Type of event (e.g., 'face_detected', 'motion_detected')
            object_name: Name of recognized object/person
            confidence: Recognition confidence (0.0 to 1.0)
            camera_source: Camera or video source identifier
            frame_path: Path to saved frame image
            description: Additional event description
            
        Returns:
            True if event logged successfully, False otherwise
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            cursor.execute('''
                INSERT INTO events 
                (timestamp, event_type, object_name, confidence, camera_source, frame_path, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, event_type, object_name, confidence, camera_source, frame_path, description))
            
            connection.commit()
            connection.close()
            
            self.logger.info(f"Event logged: {event_type} - {object_name}")
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to log event: {e}")
            return False
    
    def log_face_recognition(self, object_name: str, confidence: float,
                           camera_source: Optional[str] = None, frame_path: Optional[str] = None) -> bool:
        """
        Log a face recognition event.
        
        Args:
            object_name: Name of recognized person
            confidence: Recognition confidence
            camera_source: Camera identifier
            frame_path: Path to saved frame
            
        Returns:
            True if event logged successfully
        """
        description = f"Face recognized: {object_name} with confidence {confidence:.2f}"
        return self.log_event(
            event_type='face_recognized',
            object_name=object_name,
            confidence=confidence,
            camera_source=camera_source,
            frame_path=frame_path,
            description=description
        )
    
    def log_unknown_face(self, confidence: float, camera_source: Optional[str] = None,
                         frame_path: Optional[str] = None) -> bool:
        """
        Log an unknown face detection event.
        
        Args:
            confidence: Detection confidence
            camera_source: Camera identifier
            frame_path: Path to saved frame
            
        Returns:
            True if event logged successfully
        """
        description = f"Unknown face detected with confidence {confidence:.2f}"
        return self.log_event(
            event_type='unknown_face',
            object_name='Unknown',
            confidence=confidence,
            camera_source=camera_source,
            frame_path=frame_path,
            description=description
        )
    
    def log_motion_detection(self, camera_source: Optional[str] = None,
                            frame_path: Optional[str] = None) -> bool:
        """
        Log a motion detection event.
        
        Args:
            camera_source: Camera identifier
            frame_path: Path to saved frame
            
        Returns:
            True if event logged successfully
        """
        description = "Motion detected"
        return self.log_event(
            event_type='motion_detected',
            camera_source=camera_source,
            frame_path=frame_path,
            description=description
        )
    
    def log_system_event(self, event_type: str, description: str) -> bool:
        """
        Log a system event (e.g., camera started, recording started).
        
        Args:
            event_type: Type of system event
            description: Event description
            
        Returns:
            True if event logged successfully
        """
        return self.log_event(
            event_type=f'system_{event_type}',
            description=description
        )
    
    def get_events(self, limit: int = 100, event_type: Optional[str] = None,
                   object_name: Optional[str] = None, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get events with optional filtering.
        
        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type
            object_name: Filter by object name
            start_date: Filter events from this date (YYYY-MM-DD)
            end_date: Filter events until this date (YYYY-MM-DD)
            
        Returns:
            List of event dictionaries
        """
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            query = "SELECT * FROM events WHERE 1=1"
            params = []
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            if object_name:
                query += " AND object_name = ?"
                params.append(object_name)
            
            if start_date:
                query += " AND date(timestamp) >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND date(timestamp) <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            connection.close()
            
            events = []
            for row in rows:
                events.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'event_type': row[2],
                    'object_name': row[3],
                    'confidence': row[4],
                    'camera_source': row[5],
                    'frame_path': row[6],
                    'description': row[7],
                    'created_at': row[8]
                })
            
            return events
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get events: {e}")
            return []
    
    def get_recent_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get events from the last specified hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent events
        """
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            query = '''
                SELECT * FROM events 
                WHERE timestamp >= datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            '''.format(hours)
            
            cursor.execute(query)
            rows = cursor.fetchall()
            connection.close()
            
            events = []
            for row in rows:
                events.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'event_type': row[2],
                    'object_name': row[3],
                    'confidence': row[4],
                    'camera_source': row[5],
                    'frame_path': row[6],
                    'description': row[7],
                    'created_at': row[8]
                })
            
            return events
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get recent events: {e}")
            return []
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """
        Get event statistics.
        
        Returns:
            Dictionary with event statistics
        """
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            # Total events
            cursor.execute("SELECT COUNT(*) FROM events")
            total_events = cursor.fetchone()[0]
            
            # Events by type
            cursor.execute('''
                SELECT event_type, COUNT(*) as count 
                FROM events 
                GROUP BY event_type 
                ORDER BY count DESC
            ''')
            events_by_type = dict(cursor.fetchall())
            
            # Events by object
            cursor.execute('''
                SELECT object_name, COUNT(*) as count 
                FROM events 
                WHERE object_name IS NOT NULL 
                GROUP BY object_name 
                ORDER BY count DESC
                LIMIT 10
            ''')
            events_by_object = dict(cursor.fetchall())
            
            # Recent events (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM events 
                WHERE timestamp >= datetime('now', '-24 hours')
            ''')
            recent_events = cursor.fetchone()[0]
            
            connection.close()
            
            return {
                'total_events': total_events,
                'events_by_type': events_by_type,
                'top_objects': events_by_object,
                'recent_24h': recent_events
            }
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get event statistics: {e}")
            return {}
    
    def clear_old_events(self, days: int = 30) -> int:
        """
        Clear events older than specified days.
        
        Args:
            days: Number of days to keep events
            
        Returns:
            Number of events deleted
        """
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            cursor.execute('''
                DELETE FROM events 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days))
            
            deleted_count = cursor.rowcount
            connection.commit()
            connection.close()
            
            self.logger.info(f"Cleared {deleted_count} old events")
            return deleted_count
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to clear old events: {e}")
            return 0
    
    def export_events_to_csv(self, filename: str, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> bool:
        """
        Export events to CSV file.
        
        Args:
            filename: Output CSV filename
            start_date: Filter events from this date
            end_date: Filter events until this date
            
        Returns:
            True if exported successfully
        """
        try:
            import csv
            
            events = self.get_events(
                limit=10000,  # Large limit for export
                start_date=start_date,
                end_date=end_date
            )
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if events:
                    fieldnames = events[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(events)
            
            self.logger.info(f"Exported {len(events)} events to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export events to CSV: {e}")
            return False


# Global event logger instance
event_logger = EventLogger()

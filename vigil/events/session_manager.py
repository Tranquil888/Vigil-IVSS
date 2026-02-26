"""
Event session management for Vigil surveillance system.
Handles event grouping with configurable delays and session lifecycle.
"""

import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from vigil.database.manager import get_events_db
from vigil.utils.dataset_manager import dataset_manager
from vigil.utils.logging_config import get_events_logger
from vigil.config.settings import settings


class EventSessionManager:
    """Manages event sessions with configurable inactivity delays."""
    
    def __init__(self):
        self.logger = get_events_logger()
        self.logger.info("Initializing EventSessionManager")
        
        self.db = get_events_db()
        # Load inactivity delay from settings
        self.inactivity_delay = int(settings.get_setting('event_inactivity_delay', 10))
        
        # Session tracking
        self.current_session_id: Optional[int] = None
        self.session_start_time: Optional[float] = None
        self.last_activity_time: Optional[float] = None
        self.session_timer: Optional[threading.Timer] = None
        self.session_lock = threading.Lock()
        
        # Event counter for descriptions
        self.event_counter = 0
        self._load_event_counter()
        
        # Check for existing active sessions on startup
        self._check_existing_sessions()
        
        self.logger.info(f"EventSessionManager initialized: current_session_id={self.current_session_id}")
    
    def _load_event_counter(self) -> None:
        """Load the event counter from database."""
        try:
            # Get the latest event session to determine counter
            sessions = self.db.get_event_sessions(limit=1)
            if sessions:
                # Extract counter from description like "event00001-3-objects"
                latest_session = sessions[0]
                if latest_session.get('description'):
                    description = latest_session['description']
                    if description.startswith('event') and '-' in description:
                        try:
                            counter_part = description.split('-')[0]  # "event00001"
                            counter = int(counter_part.replace('event', ''))
                            self.event_counter = counter
                            self.logger.info(f"Loaded event counter: {self.event_counter}")
                        except ValueError:
                            self.logger.warning(f"Could not parse counter from description: {description}")
            
            self.logger.info(f"Event counter initialized to: {self.event_counter}")
            
        except Exception as e:
            self.logger.error(f"Error loading event counter: {e}")
            self.event_counter = 0
    
    def _check_existing_sessions(self) -> None:
        """Check for existing active sessions on startup."""
        try:
            # Look for sessions without end_time (active sessions)
            active_sessions = self.db.execute_query(
                "SELECT id, start_time FROM event_sessions WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
            )
            
            if active_sessions:
                session = active_sessions[0]
                session_id = session['id']
                start_time_str = session['start_time']
                
                # Parse start time
                try:
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                    start_timestamp = start_time.timestamp()
                except:
                    start_timestamp = time.time()
                
                # Set as current session
                self.current_session_id = session_id
                self.session_start_time = start_timestamp
                self.last_activity_time = start_timestamp
                
                self.logger.info(f"Resumed active session: {session_id} from {start_time_str}")
                
                # Start timer for this session
                self._reset_session_timer()
            else:
                self.logger.info("No active sessions found on startup")
                
        except Exception as e:
            self.logger.error(f"Error checking existing sessions: {e}")
    
    def _generate_event_description(self, object_count: int) -> str:
        """Generate event description with counter and object count."""
        self.event_counter += 1
        return f"event{self.event_counter:05d}-{object_count}-objects"
    
    def start_session_if_needed(self) -> Optional[int]:
        """
        Start a new event session if one is not already active.
        
        Returns:
            Session ID if started or existing, None otherwise
        """
        with self.session_lock:
            current_time = time.time()
            
            self.logger.debug(f"Session check: current_id={self.current_session_id}, last_activity={self.last_activity_time}, delay={self.inactivity_delay}")
            
            # If no active session, start one
            if self.current_session_id is None:
                self.logger.debug("No active session, starting new one")
                return self._start_new_session()
            
            # If session exists but timer expired, start new one
            elif self.last_activity_time and (current_time - self.last_activity_time) > self.inactivity_delay:
                self.logger.debug(f"Session expired ({current_time - self.last_activity_time:.1f}s > {self.inactivity_delay}s), starting new one")
                self._end_current_session()
                return self._start_new_session()
            
            # Reset timer for existing session
            else:
                self.logger.debug(f"Using existing session {self.current_session_id}")
                self._reset_session_timer()
                return self.current_session_id
        
        return None
    
    def _start_new_session(self) -> int:
        """Start a new event session."""
        try:
            current_time = time.time()
            timestamp = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Create new session with placeholder description
            session_id = self.db.create_event_session(timestamp, "active-session")
            
            self.current_session_id = session_id
            self.session_start_time = current_time
            self.last_activity_time = current_time
            
            # Start inactivity timer
            self._reset_session_timer()
            
            self.logger.info(f"Started new event session: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Error starting new session: {e}")
            return None
    
    def _end_current_session(self) -> None:
        """End the current event session."""
        if self.current_session_id is None:
            return
        
        try:
            # Cancel any pending timer
            if self.session_timer:
                self.session_timer.cancel()
                self.session_timer = None
            
            # Calculate session duration
            current_time = time.time()
            duration = int(current_time - self.session_start_time) if self.session_start_time else 0
            end_time = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Get object count for description
            objects = self.db.get_event_objects(self.current_session_id)
            object_count = len(set(obj['object_name'] for obj in objects))
            description = self._generate_event_description(object_count)
            
            # Update session in database
            self.db.end_event_session(self.current_session_id, end_time, duration)
            self.db.execute_update(
                'UPDATE event_sessions SET description = ? WHERE id = ?',
                (description, self.current_session_id)
            )
            
            self.logger.info(f"Ended event session {self.current_session_id}: {description} ({duration}s)")
            
            self.current_session_id = None
            self.session_start_time = None
            self.last_activity_time = None
            
        except Exception as e:
            self.logger.error(f"Error ending session: {e}")
    
    def _reset_session_timer(self) -> None:
        """Reset the inactivity timer for the current session."""
        if self.session_timer:
            self.session_timer.cancel()
        
        self.last_activity_time = time.time()
        self.session_timer = threading.Timer(
            self.inactivity_delay, 
            self._on_inactivity_timeout
        )
        self.session_timer.daemon = True
        self.session_timer.start()
    
    def _on_inactivity_timeout(self) -> None:
        """Handle inactivity timeout."""
        with self.session_lock:
            if self.current_session_id is not None:
                self.logger.info(f"Inactivity timeout for session {self.current_session_id}")
                self._end_current_session()
    
    def add_recognition_event(self, object_name: str, confidence: float, 
                           frame, face_location, object_type: str = "Person") -> bool:
        """
        Add a recognition event to the current session.
        
        Args:
            object_name: Name of recognized object
            confidence: Recognition confidence
            frame: Video frame
            face_location: Face coordinates (top, right, bottom, left)
            object_type: Type of object (Person, etc.)
            
        Returns:
            True if event added successfully
        """
        try:
            # Ensure we have an active session
            session_id = self.start_session_if_needed()
            if session_id is None:
                self.logger.error("Failed to get active session")
                return False
            
            self.logger.debug(f"Adding recognition to session {session_id}: {object_name}")
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Add object recognition to database
            self.db.add_event_object(
                session_id, object_name, object_type, current_time, confidence
            )
            
            # Capture face if object is known (not Unknown)
            photo_path = None
            if object_name != 'Unknown':
                photo_path = dataset_manager.capture_face(frame, face_location, object_name)
                
                if photo_path:
                    # Add photo to database
                    self.db.add_event_photo(
                        session_id, object_name, photo_path, current_time, confidence
                    )
                    self.logger.info(f"Captured face for {object_name}: {photo_path}")
            
            # Reset activity timer
            self._reset_session_timer()
            
            self.logger.debug(f"Added recognition event: {object_name} (confidence: {confidence:.2f})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding recognition event: {e}")
            return False
    
    def get_active_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active session."""
        with self.session_lock:
            if self.current_session_id is None:
                return None
            
            try:
                session = self.db.get_event_session(self.current_session_id)
                objects = self.db.get_event_objects(self.current_session_id)
                
                return {
                    'session_id': self.current_session_id,
                    'start_time': session['start_time'] if session else None,
                    'duration': int(time.time() - self.session_start_time) if self.session_start_time else 0,
                    'object_count': len(set(obj['object_name'] for obj in objects)),
                    'recognition_count': len(objects),
                    'objects': objects
                }
                
            except Exception as e:
                self.logger.error(f"Error getting active session info: {e}")
                return None
    
    def force_end_session(self) -> bool:
        """Force end the current session."""
        with self.session_lock:
            if self.current_session_id is None:
                return False
            
            self._end_current_session()
            return True
    
    def set_inactivity_delay(self, delay: int) -> None:
        """Update the inactivity delay."""
        self.inactivity_delay = max(1, delay)  # Minimum 1 second
        
        # Save to settings
        settings.set_setting('event_inactivity_delay', str(self.inactivity_delay))
        
        self.logger.info(f"Updated inactivity delay to {self.inactivity_delay} seconds")
    
    def shutdown(self) -> None:
        """Clean shutdown of the session manager."""
        with self.session_lock:
            if self.session_timer:
                self.session_timer.cancel()
                self.session_timer = None
            
            if self.current_session_id is not None:
                self._end_current_session()
            
            # Fix any orphaned sessions (sessions without end_time)
            self._fix_orphaned_sessions()
    
    def _fix_orphaned_sessions(self) -> None:
        """Fix sessions that were not properly ended."""
        try:
            # Get all sessions without end_time
            orphaned = self.db.execute_query(
                "SELECT id, start_time FROM event_sessions WHERE end_time IS NULL"
            )
            
            for session in orphaned:
                session_id = session['id']
                start_time_str = session['start_time']
                
                # Parse start time
                try:
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                    start_timestamp = start_time.timestamp()
                except:
                    start_timestamp = time.time()
                
                # Calculate duration as time since start
                duration = int(time.time() - start_timestamp)
                end_time = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
                
                # Get object count for description
                objects = self.db.get_event_objects(session_id)
                object_count = len(set(obj['object_name'] for obj in objects))
                description = self._generate_event_description(object_count)
                
                # Update session
                self.db.end_event_session(session_id, end_time, duration)
                self.db.execute_update(
                    'UPDATE event_sessions SET description = ? WHERE id = ?',
                    (description, session_id)
                )
                
                self.logger.info(f"Fixed orphaned session {session_id}: {description} ({duration}s)")
                
        except Exception as e:
            self.logger.error(f"Error fixing orphaned sessions: {e}")


# Global session manager instance
session_manager = EventSessionManager()

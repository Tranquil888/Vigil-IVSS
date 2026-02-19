"""
Face detection module for Vigil surveillance system.
"""

import cv2
import face_recognition
import numpy as np
import os
import pickle
from typing import List, Tuple, Optional, Dict, Any
from vigil.core.exceptions import RecognitionError
from vigil.utils.logging_config import get_recognition_logger
from vigil.config.settings import settings
from vigil.recognition.face_trainer import FaceTrainer


class FaceDetector:
    """Handles face detection and recognition using face_recognition library."""
    
    def __init__(self):
        self.logger = get_recognition_logger()
        self.algorithm = "cnn"  # Default algorithm
        self.tolerance = 0.6  # Default tolerance
        self.face_encodings = {}
        self.face_names = []
        self.model_path = ""
        self._load_settings()
        self._load_encodings()
    
    def _load_settings(self) -> None:
        """Load recognition settings from configuration."""
        try:
            self.algorithm = settings.get_setting('model_algorithm', 'cnn')
            self.tolerance = float(settings.get_setting('recognition_tolerance', 0.6))
            base_path = settings.get_setting('base_path', os.getcwd())
            self.model_path = settings.get_setting(
                'model_path',
                os.path.join(base_path, 'data', 'encodings.pickle')
            )
            self.logger.info(f"Face detection algorithm: {self.algorithm}, tolerance: {self.tolerance}")
        except Exception as e:
            self.logger.error(f"Error loading recognition settings: {e}")
            self.algorithm = "cnn"
            self.tolerance = 0.6
            self.model_path = os.path.join(os.getcwd(), "data", "encodings.pickle")
    
    def _load_encodings(self) -> None:
        """Load face encodings from pickle file."""
        try:
            if not self.model_path:
                self.model_path = os.path.join(os.getcwd(), "data", "encodings.pickle")
            
            if os.path.exists(self.model_path):
                with open(self.model_path, "rb") as f:
                    data = pickle.loads(f.read())
                    
                    # Handle both old and new format
                    if "encodings" in data and isinstance(data["encodings"], dict):
                        # New format: dict of name -> encoding
                        self.face_encodings = data["encodings"]
                        self.face_names = list(self.face_encodings.keys())
                    elif "encodings" in data and "names" in data:
                        # Old format: lists of encodings and names
                        encodings_list = data["encodings"]
                        names_list = data["names"]
                        self.face_encodings = {}
                        for encoding, name in zip(encodings_list, names_list):
                            if name not in self.face_encodings:
                                self.face_encodings[name] = []
                            self.face_encodings[name].append(encoding)
                        self.face_names = list(self.face_encodings.keys())
                    
                    # Load additional settings if available
                    if "algorithm" in data:
                        self.algorithm = data["algorithm"]
                    if "tolerance" in data:
                        self.tolerance = data["tolerance"]
                
                self.logger.info(f"Loaded {len(self.face_names)} face encodings from {self.model_path}")
            else:
                self.logger.warning(f"No encodings file found at {self.model_path}")
                
        except Exception as e:
            self.logger.error(f"Error loading face encodings: {e}")
            self.face_encodings = {}
            self.face_names = []
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in a frame.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of face bounding boxes (top, right, bottom, left)
        """
        try:
            # Convert BGR to RGB for face_recognition library
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(
                rgb_frame, 
                model=self.algorithm
            )
            
            return face_locations
            
        except Exception as e:
            self.logger.error(f"Error detecting faces: {e}")
            raise RecognitionError(f"Failed to detect faces: {e}")
    
    def encode_faces(self, frame: np.ndarray, face_locations: List[Tuple[int, int, int, int]]) -> List[np.ndarray]:
        """
        Encode detected faces.
        
        Args:
            frame: Input frame (BGR format)
            face_locations: List of face bounding boxes
            
        Returns:
            List of face encodings
        """
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(
                rgb_frame, 
                face_locations
            )
            
            return face_encodings
            
        except Exception as e:
            self.logger.error(f"Error encoding faces: {e}")
            raise RecognitionError(f"Failed to encode faces: {e}")
    
    def recognize_faces(self, frame: np.ndarray, tolerance: float = None) -> List[Dict[str, Any]]:
        """
        Detect and recognize faces in a frame.
        
        Args:
            frame: Input frame (BGR format)
            tolerance: Face recognition tolerance (uses default if None)
            
        Returns:
            List of recognized face information
        """
        if tolerance is None:
            tolerance = self.tolerance
            
        try:
            # Detect faces
            face_locations = self.detect_faces(frame)
            
            if not face_locations:
                return []
            
            # Encode faces
            face_encodings = self.encode_faces(frame, face_locations)
            
            # Recognize faces
            recognized_faces = []
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Compare with known faces
                # Handle both single encodings and multiple encodings per person
                all_encodings = []
                all_names = []
                
                for name, encodings in self.face_encodings.items():
                    if isinstance(encodings, list):
                        all_encodings.extend(encodings)
                        all_names.extend([name] * len(encodings))
                    else:
                        all_encodings.append(encodings)
                        all_names.append(name)
                
                if not all_encodings:
                    # No known faces, add as unknown
                    recognized_faces.append({
                        'name': "Unknown",
                        'confidence': 0.0,
                        'location': (top, right, bottom, left),
                        'box': (left, top, right - left, bottom - top)
                    })
                    continue
                
                matches = face_recognition.compare_faces(
                    all_encodings,
                    face_encoding,
                    tolerance=tolerance
                )
                
                name = "Unknown"
                confidence = 0.0
                
                if True in matches:
                    # Find best match
                    face_distances = face_recognition.face_distance(
                        all_encodings,
                        face_encoding
                    )
                    
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = all_names[best_match_index]
                        confidence = 1.0 - face_distances[best_match_index]
                
                recognized_faces.append({
                    'name': name,
                    'confidence': confidence,
                    'location': (top, right, bottom, left),
                    'box': (left, top, right - left, bottom - top)  # (x, y, w, h)
                })
            
            return recognized_faces
            
        except Exception as e:
            self.logger.error(f"Error recognizing faces: {e}")
            raise RecognitionError(f"Failed to recognize faces: {e}")
    
    def draw_face_boxes(self, frame: np.ndarray, faces: List[Dict[str, Any]]) -> np.ndarray:
        """
        Draw bounding boxes and labels for recognized faces.
        
        Args:
            frame: Input frame
            faces: List of recognized face information
            
        Returns:
            Frame with face boxes and labels drawn
        """
        try:
            result_frame = frame.copy()
            
            for face in faces:
                name = face['name']
                confidence = face['confidence']
                box = face['box']  # (x, y, w, h)
                x, y, w, h = box
                
                # Determine color based on recognition
                if name == "Unknown":
                    color = (0, 0, 255)  # Red for unknown
                elif confidence > 0.8:
                    color = (0, 255, 0)  # Green for high confidence
                elif confidence > 0.6:
                    color = (0, 255, 255)  # Yellow for medium confidence
                else:
                    color = (255, 0, 0)  # Blue for low confidence
                
                # Draw rectangle
                cv2.rectangle(result_frame, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                label = f"{name} ({confidence:.2f})" if name != "Unknown" else name
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                
                # Draw label background
                cv2.rectangle(result_frame, (x, y - label_size[1] - 10), 
                            (x + label_size[0], y), color, -1)
                
                # Draw label text
                cv2.putText(result_frame, label, (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            return result_frame
            
        except Exception as e:
            self.logger.error(f"Error drawing face boxes: {e}")
            return frame
    
    def add_face_encoding(self, name: str, encoding: np.ndarray) -> bool:
        """
        Add a new face encoding to the database.
        
        Args:
            name: Person name
            encoding: Face encoding array
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            self.face_encodings[name] = encoding
            
            if name not in self.face_names:
                self.face_names.append(name)
            
            self.logger.info(f"Added face encoding for: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding face encoding: {e}")
            return False
    
    def remove_face_encoding(self, name: str) -> bool:
        """
        Remove a face encoding from the database.
        
        Args:
            name: Person name to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            if name in self.face_encodings:
                del self.face_encodings[name]
                
            if name in self.face_names:
                self.face_names.remove(name)
            
            self.logger.info(f"Removed face encoding for: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing face encoding: {e}")
            return False
    
    def save_encodings(self, filename: str = None) -> bool:
        """
        Save face encodings to pickle file.
        
        Args:
            filename: Output filename (uses default path if None)
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if filename is None:
                filename = self.model_path
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            data = {
                "encodings": self.face_encodings,
                "algorithm": self.algorithm,
                "tolerance": self.tolerance,
                "training_time": 0,
                "total_images": 0,
                "processed_faces": sum(len(encodings) if isinstance(encodings, list) else 1 
                                      for encodings in self.face_encodings.values()),
                "unique_faces": len(self.face_names)
            }
            
            with open(filename, "wb") as f:
                f.write(pickle.dumps(data))
            
            self.logger.info(f"Saved {len(self.face_names)} face encodings to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving face encodings: {e}")
            return False
    
    def get_known_faces_count(self) -> int:
        """Get the number of known faces."""
        return len(self.face_names)
    
    def get_known_faces_list(self) -> List[str]:
        """Get list of known face names."""
        return self.face_names.copy()
    
    def is_trained(self) -> bool:
        """Check if the face recognition model is trained."""
        return len(self.face_encodings) > 0
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'is_trained': self.is_trained(),
            'known_faces_count': len(self.face_names),
            'known_faces': self.face_names.copy(),
            'algorithm': self.algorithm,
            'tolerance': self.tolerance,
            'model_path': self.model_path,
            'model_exists': os.path.exists(self.model_path) if self.model_path else False
        }
    
    def set_algorithm(self, algorithm: str) -> bool:
        """
        Set the face detection algorithm.
        
        Args:
            algorithm: 'cnn' or 'hog'
            
        Returns:
            True if successful, False otherwise
        """
        if algorithm not in ["cnn", "hog"]:
            return False
        
        self.algorithm = algorithm
        self.logger.info(f"Face detection algorithm set to: {algorithm}")
        return True
    
    def set_tolerance(self, tolerance: float) -> bool:
        """
        Set the face recognition tolerance.
        
        Args:
            tolerance: Value between 0.0 and 1.0
            
        Returns:
            True if successful, False otherwise
        """
        if not 0.0 <= tolerance <= 1.0:
            return False
        
        self.tolerance = tolerance
        self.logger.info(f"Face recognition tolerance set to: {tolerance}")
        return True
    
    def reload_encodings(self) -> bool:
        """
        Reload face encodings from the model file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._load_encodings()
            return True
        except Exception as e:
            self.logger.error(f"Error reloading encodings: {e}")
            return False


# Global face detector instance
face_detector = FaceDetector()

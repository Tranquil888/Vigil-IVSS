"""
Face training module for Vigil surveillance system.
Extracts and modularizes training functionality from original main.py.
"""

import os
import pickle
import time
import cv2
import numpy as np
import face_recognition
from imutils import paths
from typing import List, Tuple, Dict, Any, Optional, Callable
from vigil.core.exceptions import TrainingError
from vigil.utils.logging_config import get_recognition_logger
from vigil.utils.dataset_manager import DatasetManager


class FaceTrainer:
    """Handles face recognition model training from dataset images."""
    
    def __init__(self):
        self.logger = get_recognition_logger()
        self.dataset_manager = DatasetManager()
        self.algorithm = "cnn"  # Default algorithm
        self.tolerance = 0.6
        self.is_training = False
        self.progress_callback: Optional[Callable] = None
        
    def set_algorithm(self, algorithm: str) -> None:
        """Set the face detection algorithm."""
        if algorithm not in ["cnn", "hog"]:
            raise ValueError("Algorithm must be 'cnn' or 'hog'")
        self.algorithm = algorithm
        self.logger.info(f"Face detection algorithm set to: {algorithm}")
    
    def set_tolerance(self, tolerance: float) -> None:
        """Set face recognition tolerance."""
        if not 0.0 <= tolerance <= 1.0:
            raise ValueError("Tolerance must be between 0.0 and 1.0")
        self.tolerance = tolerance
        self.logger.info(f"Face recognition tolerance set to: {tolerance}")
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """Set callback function for progress updates."""
        self.progress_callback = callback
    
    def _update_progress(self, current: int, total: int, message: str = "") -> None:
        """Update progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def validate_dataset(self, dataset_path: str) -> Dict[str, Any]:
        """
        Validate the training dataset.
        
        Args:
            dataset_path: Path to the dataset directory
            
        Returns:
            Dictionary with validation results
        """
        try:
            return self.dataset_manager.validate_dataset(dataset_path)
        except Exception as e:
            self.logger.error(f"Dataset validation failed: {e}")
            raise TrainingError(f"Dataset validation failed: {e}")
    
    def train_model(self, dataset_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Train face recognition model from dataset.
        
        Args:
            dataset_path: Path to the dataset directory
            output_path: Path to save the trained model (optional)
            
        Returns:
            Dictionary with training results
        """
        if self.is_training:
            raise TrainingError("Training is already in progress")
        
        try:
            self.is_training = True
            self.logger.info("Starting face recognition model training")
            
            # Validate dataset
            validation_result = self.validate_dataset(dataset_path)
            if not validation_result['valid']:
                raise TrainingError(f"Invalid dataset: {validation_result['errors']}")
            
            # Set default output path
            if output_path is None:
                output_path = os.path.join(os.getcwd(), "data", "encodings.pickle")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get all image paths
            image_paths = list(paths.list_images(dataset_path))
            total_images = len(image_paths)
            
            if total_images == 0:
                raise TrainingError("No training images found in dataset")
            
            self.logger.info(f"Found {total_images} training images")
            self._update_progress(0, total_images, "Starting training...")
            
            # Initialize encodings and names lists
            known_encodings = []
            known_names = []
            
            # Process each image
            start_time = time.time()
            processed_count = 0
            
            for i, image_path in enumerate(image_paths):
                try:
                    # Update progress
                    progress_message = f"Processing {os.path.basename(image_path)}"
                    self._update_progress(i, total_images, progress_message)
                    
                    # Load image and extract name from path
                    image = cv2.imread(image_path)
                    if image is None:
                        self.logger.warning(f"Could not read image: {image_path}")
                        continue
                    
                    # Extract name from directory structure (remove prefix if present)
                    name = os.path.basename(os.path.dirname(image_path))
                    # Remove common prefixes if present
                    if name.startswith("_"):
                        name = name[13:] if len(name) > 13 else name
                    elif name.startswith("dataset_"):
                        name = name[8:]  # Remove "dataset_" prefix
                    elif name.startswith("user_"):
                        name = name[5:]   # Remove "user_" prefix
                    
                    # Clean up name
                    name = name.strip().replace("_", " ").title()
                    
                    self.logger.debug(f"Processing image for person: '{name}' (original: '{os.path.basename(os.path.dirname(image_path))}')")
                    
                    # Convert BGR to RGB
                    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    # Detect face locations
                    boxes = face_recognition.face_locations(rgb, model=self.algorithm)
                    
                    # Generate face encodings
                    for encoding in face_recognition.face_encodings(rgb, boxes):
                        known_encodings.append(encoding)
                        known_names.append(name)
                        processed_count += 1
                    
                    self.logger.debug(f"Processed {i+1}/{total_images}: {image_path}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing image {image_path}: {e}")
                    continue
            
            # Check if any faces were found
            if len(known_encodings) == 0:
                raise TrainingError("No faces found in training images")
            
            # Create training data
            training_data = {
                'encodings': known_encodings,
                'names': known_names,
                'algorithm': self.algorithm,
                'tolerance': self.tolerance,
                'training_time': time.time() - start_time,
                'total_images': total_images,
                'processed_faces': len(known_encodings),
                'unique_faces': len(set(known_names))
            }
            
            # Save training data
            with open(output_path, 'wb') as f:
                f.write(pickle.dumps(training_data))
            
            # Calculate training statistics
            end_time = time.time()
            training_time = end_time - start_time
            
            results = {
                'success': True,
                'output_path': output_path,
                'total_images': total_images,
                'processed_faces': len(known_encodings),
                'unique_faces': len(set(known_names)),
                'training_time': training_time,
                'algorithm': self.algorithm,
                'tolerance': self.tolerance,
                'faces_per_second': len(known_encodings) / training_time if training_time > 0 else 0
            }
            
            self.logger.info(f"Training completed successfully: {results}")
            self._update_progress(total_images, total_images, "Training completed!")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            raise TrainingError(f"Training failed: {e}")
        finally:
            self.is_training = False
    
    def load_trained_model(self, model_path: str) -> Dict[str, Any]:
        """
        Load a trained face recognition model.
        
        Args:
            model_path: Path to the trained model file
            
        Returns:
            Dictionary with model data
        """
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")
            
            with open(model_path, 'rb') as f:
                data = pickle.loads(f.read())
            
            # Validate model structure
            if 'encodings' not in data or 'names' not in data:
                raise ValueError("Invalid model structure: missing encodings or names")
            
            self.logger.info(f"Loaded model with {len(data['encodings'])} face encodings")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise TrainingError(f"Failed to load model: {e}")
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status."""
        return {
            'is_training': self.is_training,
            'algorithm': self.algorithm,
            'tolerance': self.tolerance
        }
    
    def create_sample_dataset_structure(self, base_path: str) -> bool:
        """
        Create a sample dataset directory structure.
        
        Args:
            base_path: Base path for the dataset
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.dataset_manager.create_sample_structure(base_path)
        except Exception as e:
            self.logger.error(f"Error creating dataset structure: {e}")
            return False


# Global face trainer instance
face_trainer = FaceTrainer()

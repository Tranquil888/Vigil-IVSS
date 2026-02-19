"""
Training service for Vigil surveillance system.
High-level coordination of face recognition training operations.
"""

import os
import threading
import time
from typing import Dict, Any, Optional, Callable
from vigil.recognition.face_trainer import FaceTrainer
from vigil.recognition.face_detector import FaceDetector
from vigil.utils.dataset_manager import DatasetManager
from vigil.utils.logging_config import get_recognition_logger
from vigil.config.settings import settings


class TrainingService:
    """High-level service for coordinating face recognition training."""
    
    def __init__(self):
        self.logger = get_recognition_logger()
        self.face_trainer = FaceTrainer()
        self.face_detector = FaceDetector()
        self.dataset_manager = DatasetManager()
        
        # Training state
        self.is_training = False
        self.training_thread: Optional[threading.Thread] = None
        self.last_training_result: Optional[Dict[str, Any]] = None
        
        # Callbacks
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
        
        # Configuration
        self.dataset_path = ""
        self.model_path = ""
        self.archive_path = ""
        
        self._load_configuration()
        self._setup_trainer_callbacks()
    
    def _load_configuration(self) -> None:
        """Load training configuration from settings."""
        try:
            # Get paths from settings or use defaults
            base_path = settings.get_setting('base_path', os.getcwd())
            
            self.dataset_path = settings.get_setting(
                'dataset_path', 
                os.path.join(base_path, 'data', 'dataset')
            )
            
            self.model_path = settings.get_setting(
                'model_path',
                os.path.join(base_path, 'data', 'encodings.pickle')
            )
            
            self.archive_path = settings.get_setting(
                'archive_path',
                os.path.join(base_path, 'data', 'data_archives', 'dataset_archives')
            )
            
            # Set trainer configuration
            algorithm = settings.get_setting('model_algorithm', 'cnn')
            tolerance = float(settings.get_setting('recognition_tolerance', 0.6))
            
            self.face_trainer.set_algorithm(algorithm)
            self.face_trainer.set_tolerance(tolerance)
            
            self.logger.info(f"Training configuration loaded: algorithm={algorithm}, tolerance={tolerance}")
            
        except Exception as e:
            self.logger.error(f"Error loading training configuration: {e}")
            # Use default values
            base_path = os.getcwd()
            self.dataset_path = os.path.join(base_path, 'data', 'dataset')
            self.model_path = os.path.join(base_path, 'data', 'encodings.pickle')
            self.archive_path = os.path.join(base_path, 'data', 'data_archives', 'dataset_archives')
    
    def _setup_trainer_callbacks(self) -> None:
        """Setup callbacks for the face trainer."""
        def progress_handler(current: int, total: int, message: str) -> None:
            if self.progress_callback:
                self.progress_callback(current, total, message)
        
        self.face_trainer.set_progress_callback(progress_handler)
    
    def set_callbacks(self, 
                     progress_callback: Optional[Callable] = None,
                     completion_callback: Optional[Callable] = None) -> None:
        """
        Set callbacks for training operations.
        
        Args:
            progress_callback: Function to call with progress updates
            completion_callback: Function to call when training completes
        """
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
    
    def validate_dataset(self) -> Dict[str, Any]:
        """
        Validate the current training dataset.
        
        Returns:
            Dictionary with validation results
        """
        try:
            return self.dataset_manager.validate_dataset(self.dataset_path)
        except Exception as e:
            self.logger.error(f"Dataset validation failed: {e}")
            return {'valid': False, 'errors': [str(e)]}
    
    def get_dataset_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the current dataset.
        
        Returns:
            Dictionary with dataset statistics
        """
        try:
            return self.dataset_manager.get_dataset_statistics(self.dataset_path)
        except Exception as e:
            self.logger.error(f"Error getting dataset statistics: {e}")
            return {}
    
    def start_training(self, dataset_path: str = None, model_path: str = None) -> bool:
        """
        Start face recognition model training in a separate thread.
        
        Args:
            dataset_path: Custom dataset path (optional)
            model_path: Custom model output path (optional)
            
        Returns:
            True if training started successfully, False otherwise
        """
        if self.is_training:
            self.logger.warning("Training is already in progress")
            return False
        
        try:
            # Use custom paths if provided, otherwise use configured paths
            train_dataset_path = dataset_path or self.dataset_path
            train_model_path = model_path or self.model_path
            
            # Validate dataset first
            validation_result = self.validate_dataset()
            if not validation_result['valid']:
                self.logger.error(f"Dataset validation failed: {validation_result['errors']}")
                return False
            
            # Start training in separate thread
            self.training_thread = threading.Thread(
                target=self._training_worker,
                args=(train_dataset_path, train_model_path),
                daemon=True
            )
            
            self.is_training = True
            self.training_thread.start()
            
            self.logger.info("Training started in background thread")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start training: {e}")
            return False
    
    def _training_worker(self, dataset_path: str, model_path: str) -> None:
        """
        Worker function for training operations.
        
        Args:
            dataset_path: Path to training dataset
            model_path: Path to save trained model
        """
        try:
            self.logger.info("Training worker started")
            
            # Perform training
            result = self.face_trainer.train_model(dataset_path, model_path)
            
            # Update face detector with new model
            if result['success']:
                try:
                    self.face_detector._load_encodings()
                    self.logger.info("Face detector updated with new model")
                except Exception as e:
                    self.logger.error(f"Error updating face detector: {e}")
            
            # Store result
            self.last_training_result = result
            
            # Call completion callback
            if self.completion_callback:
                self.completion_callback(result)
            
            self.logger.info(f"Training completed: {result}")
            
        except Exception as e:
            self.logger.error(f"Training worker failed: {e}")
            error_result = {
                'success': False,
                'error': str(e),
                'message': 'Training failed due to an error'
            }
            self.last_training_result = error_result
            
            if self.completion_callback:
                self.completion_callback(error_result)
        
        finally:
            self.is_training = False
    
    def stop_training(self) -> bool:
        """
        Stop the current training operation.
        
        Returns:
            True if training was stopped, False if no training was in progress
        """
        if not self.is_training:
            return False
        
        try:
            # Note: face_recognition library doesn't support graceful interruption
            # This will set the flag and let the current operation complete
            self.is_training = False
            self.logger.info("Training stop requested")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping training: {e}")
            return False
    
    def get_training_status(self) -> Dict[str, Any]:
        """
        Get current training status.
        
        Returns:
            Dictionary with training status information
        """
        trainer_status = self.face_trainer.get_training_status()
        
        return {
            'is_training': self.is_training,
            'trainer_status': trainer_status,
            'dataset_path': self.dataset_path,
            'model_path': self.model_path,
            'last_result': self.last_training_result,
            'dataset_exists': os.path.exists(self.dataset_path),
            'model_exists': os.path.exists(self.model_path)
        }
    
    def create_dataset_structure(self) -> bool:
        """
        Create the dataset directory structure.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.dataset_manager.create_sample_structure(self.dataset_path)
        except Exception as e:
            self.logger.error(f"Error creating dataset structure: {e}")
            return False
    
    def add_person_images(self, person_name: str, image_paths: list) -> bool:
        """
        Add training images for a person.
        
        Args:
            person_name: Name of the person
            image_paths: List of image file paths
            
        Returns:
            True if all images were added successfully, False otherwise
        """
        try:
            success_count = 0
            for image_path in image_paths:
                if self.dataset_manager.add_training_image(
                    self.dataset_path, person_name, image_path
                ):
                    success_count += 1
            
            self.logger.info(f"Added {success_count}/{len(image_paths)} images for {person_name}")
            return success_count == len(image_paths)
            
        except Exception as e:
            self.logger.error(f"Error adding person images: {e}")
            return False
    
    def remove_person(self, person_name: str, archive: bool = True) -> bool:
        """
        Remove a person from the dataset.
        
        Args:
            person_name: Name of the person to remove
            archive: Whether to archive the person's data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            archive_path = self.archive_path if archive else None
            return self.dataset_manager.remove_person_directory(
                self.dataset_path, person_name, archive_path
            )
        except Exception as e:
            self.logger.error(f"Error removing person: {e}")
            return False
    
    def list_persons(self) -> list:
        """
        List all persons in the dataset.
        
        Returns:
            List of person names
        """
        try:
            return self.dataset_manager.list_persons(self.dataset_path)
        except Exception as e:
            self.logger.error(f"Error listing persons: {e}")
            return []
    
    def cleanup_dataset(self) -> int:
        """
        Clean up empty directories in the dataset.
        
        Returns:
            Number of directories removed
        """
        try:
            return self.dataset_manager.cleanup_empty_directories(self.dataset_path)
        except Exception as e:
            self.logger.error(f"Error cleaning up dataset: {e}")
            return 0
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current trained model.
        
        Returns:
            Dictionary with model information
        """
        try:
            if not os.path.exists(self.model_path):
                return {'exists': False, 'message': 'No trained model found'}
            
            model_data = self.face_trainer.load_trained_model(self.model_path)
            
            return {
                'exists': True,
                'path': self.model_path,
                'total_encodings': len(model_data.get('encodings', [])),
                'unique_faces': len(set(model_data.get('names', []))),
                'algorithm': model_data.get('algorithm', 'unknown'),
                'tolerance': model_data.get('tolerance', 0.6),
                'training_time': model_data.get('training_time', 0),
                'file_size': os.path.getsize(self.model_path)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting model info: {e}")
            return {'exists': False, 'error': str(e)}


# Global training service instance
training_service = TrainingService()

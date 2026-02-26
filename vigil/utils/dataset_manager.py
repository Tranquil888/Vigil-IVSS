"""
Dataset management utilities for Vigil surveillance system.
Handles dataset operations, validation, and statistics.
"""

import os
import shutil
import time
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
from vigil.utils.logging_config import get_utils_logger


class DatasetManager:
    """Manages training datasets for face recognition."""
    
    def __init__(self):
        self.logger = get_utils_logger()
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        
    def validate_dataset(self, dataset_path: str) -> Dict[str, Any]:
        """
        Validate the training dataset structure and contents.
        
        Args:
            dataset_path: Path to the dataset directory
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            # Check if dataset directory exists
            if not os.path.exists(dataset_path):
                result['errors'].append(f"Dataset directory does not exist: {dataset_path}")
                return result
            
            if not os.path.isdir(dataset_path):
                result['errors'].append(f"Dataset path is not a directory: {dataset_path}")
                return result
            
            # Get all subdirectories (person folders)
            person_dirs = []
            for item in os.listdir(dataset_path):
                item_path = os.path.join(dataset_path, item)
                if os.path.isdir(item_path):
                    person_dirs.append(item)
            
            if not person_dirs:
                result['errors'].append("No person directories found in dataset")
                return result
            
            # Validate each person directory
            total_images = 0
            valid_images = 0
            person_stats = {}
            
            for person_dir in person_dirs:
                person_path = os.path.join(dataset_path, person_dir)
                images = []
                
                for file in os.listdir(person_path):
                    file_path = os.path.join(person_path, file)
                    if os.path.isfile(file_path):
                        # Check file extension
                        _, ext = os.path.splitext(file.lower())
                        if ext in self.supported_formats:
                            try:
                                # Try to open image to validate it
                                with Image.open(file_path) as img:
                                    img.verify()
                                images.append(file)
                                valid_images += 1
                            except Exception as e:
                                result['warnings'].append(f"Invalid image file: {file_path} - {e}")
                        else:
                            result['warnings'].append(f"Unsupported file format: {file_path}")
                
                total_images += len(images)
                
                if not images:
                    result['warnings'].append(f"No valid images found in directory: {person_dir}")
                else:
                    person_stats[person_dir] = {
                        'image_count': len(images),
                        'images': images
                    }
            
            # Set validation results
            result['valid'] = len(result['errors']) == 0 and valid_images > 0
            result['statistics'] = {
                'total_persons': len(person_dirs),
                'total_images': total_images,
                'valid_images': valid_images,
                'persons_with_images': len(person_stats),
                'person_details': person_stats
            }
            
            self.logger.info(f"Dataset validation completed: {result['statistics']}")
            
        except Exception as e:
            result['errors'].append(f"Validation error: {e}")
            self.logger.error(f"Dataset validation failed: {e}")
        
        return result
    
    def get_dataset_statistics(self, dataset_path: str) -> Dict[str, Any]:
        """
        Get detailed statistics about the dataset.
        
        Args:
            dataset_path: Path to the dataset directory
            
        Returns:
            Dictionary with dataset statistics
        """
        try:
            validation_result = self.validate_dataset(dataset_path)
            stats = validation_result.get('statistics', {})
            
            # Calculate additional statistics
            if stats.get('valid_images', 0) > 0:
                stats['images_per_person'] = stats['valid_images'] / max(stats['persons_with_images'], 1)
            else:
                stats['images_per_person'] = 0
            
            # Get directory size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(dataset_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
            
            stats['total_size_bytes'] = total_size
            stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting dataset statistics: {e}")
            return {}
    
    def create_person_directory(self, dataset_path: str, person_name: str) -> bool:
        """
        Create a directory for a person's training images.
        
        Args:
            dataset_path: Path to the dataset directory
            person_name: Name of the person
            
        Returns:
            True if successful, False otherwise
        """
        try:
            person_path = os.path.join(dataset_path, person_name)
            os.makedirs(person_path, exist_ok=True)
            self.logger.info(f"Created person directory: {person_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating person directory: {e}")
            return False
    
    def add_training_image(self, dataset_path: str, person_name: str, image_path: str) -> bool:
        """
        Add a training image to a person's directory.
        
        Args:
            dataset_path: Path to the dataset directory
            person_name: Name of the person
            image_path: Path to the image file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate image
            with Image.open(image_path) as img:
                img.verify()
            
            # Create person directory if it doesn't exist
            person_path = os.path.join(dataset_path, person_name)
            os.makedirs(person_path, exist_ok=True)
            
            # Generate unique filename
            _, ext = os.path.splitext(image_path)
            timestamp = int(time.time())
            filename = f"{person_name}_{timestamp}{ext}"
            dest_path = os.path.join(person_path, filename)
            
            # Copy image
            shutil.copy2(image_path, dest_path)
            self.logger.info(f"Added training image: {dest_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding training image: {e}")
            return False
    
    def remove_person_directory(self, dataset_path: str, person_name: str, archive_path: str = None) -> bool:
        """
        Remove a person's directory, optionally archiving it first.
        
        Args:
            dataset_path: Path to the dataset directory
            person_name: Name of the person
            archive_path: Path to archive directory (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            person_path = os.path.join(dataset_path, person_name)
            
            if not os.path.exists(person_path):
                self.logger.warning(f"Person directory does not exist: {person_path}")
                return False
            
            # Archive if path provided
            if archive_path:
                os.makedirs(archive_path, exist_ok=True)
                archive_dest = os.path.join(archive_path, person_name)
                shutil.move(person_path, archive_dest)
                self.logger.info(f"Archived person directory: {person_path} -> {archive_dest}")
            else:
                shutil.rmtree(person_path)
                self.logger.info(f"Removed person directory: {person_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing person directory: {e}")
            return False
    
    def list_persons(self, dataset_path: str) -> List[str]:
        """
        List all persons in the dataset.
        
        Args:
            dataset_path: Path to the dataset directory
            
        Returns:
            List of person names
        """
        try:
            if not os.path.exists(dataset_path):
                return []
            
            persons = []
            for item in os.listdir(dataset_path):
                item_path = os.path.join(dataset_path, item)
                if os.path.isdir(item_path):
                    persons.append(item)
            
            return sorted(persons)
            
        except Exception as e:
            self.logger.error(f"Error listing persons: {e}")
            return []
    
    def create_sample_structure(self, base_path: str) -> bool:
        """
        Create a sample dataset directory structure.
        
        Args:
            base_path: Base path for the dataset
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create main dataset directory
            os.makedirs(base_path, exist_ok=True)
            
            # Create sample person directories
            sample_persons = ['person_01', 'person_02', 'person_03']
            
            for person in sample_persons:
                person_path = os.path.join(base_path, person)
                os.makedirs(person_path, exist_ok=True)
                
                # Create a README file in each directory
                readme_path = os.path.join(person_path, 'README.txt')
                with open(readme_path, 'w') as f:
                    f.write(f"Add training images for {person} in this directory.\n")
                    f.write("Supported formats: .jpg, .jpeg, .png, .bmp, .tiff\n")
                    f.write("Images should contain clear frontal views of the person's face.\n")
            
            # Create main README
            readme_path = os.path.join(base_path, 'README.txt')
            with open(readme_path, 'w') as f:
                f.write("Vigil Face Recognition Dataset\n")
                f.write("================================\n\n")
                f.write("Each subdirectory contains training images for one person.\n")
                f.write("Directory names should be unique identifiers for each person.\n\n")
                f.write("To train the model:\n")
                f.write("1. Add images to person directories\n")
                f.write("2. Run the training process\n")
                f.write("3. The system will generate face encodings from these images\n")
            
            self.logger.info(f"Created sample dataset structure: {base_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating sample structure: {e}")
            return False
    
    def cleanup_empty_directories(self, dataset_path: str) -> int:
        """
        Remove empty person directories from the dataset.
        
        Args:
            dataset_path: Path to the dataset directory
            
        Returns:
            Number of directories removed
        """
        try:
            removed_count = 0
            
            if not os.path.exists(dataset_path):
                return 0
            
            for item in os.listdir(dataset_path):
                item_path = os.path.join(dataset_path, item)
                if os.path.isdir(item_path):
                    # Check if directory is empty or contains only unsupported files
                    has_images = False
                    for file in os.listdir(item_path):
                        _, ext = os.path.splitext(file.lower())
                        if ext in self.supported_formats:
                            has_images = True
                            break
                    
                    if not has_images:
                        shutil.rmtree(item_path)
                        removed_count += 1
                        self.logger.info(f"Removed empty directory: {item_path}")
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up empty directories: {e}")
            return 0
    
    def capture_face(self, frame: np.ndarray, face_location: Tuple[int, int, int, int], 
                   object_name: str) -> Optional[str]:
        """
        Capture and save a face frame from video stream.
        
        Args:
            frame: Video frame containing the face
            face_location: Tuple of (top, right, bottom, left) face coordinates
            object_name: Name of the recognized object
            
        Returns:
            Path to saved face image, or None if failed
        """
        try:
            # Extract face coordinates
            top, right, bottom, left = face_location
            
            # Add padding around the face
            padding = 20
            top = max(0, top - padding)
            left = max(0, left - padding)
            bottom = min(frame.shape[0], bottom + padding)
            right = min(frame.shape[1], right + padding)
            
            # Extract face ROI
            face_roi = frame[top:bottom, left:right]
            
            if face_roi.size == 0:
                self.logger.warning("Empty face ROI detected")
                return None
            
            # Create captured faces directory structure
            base_dir = os.path.join(os.getcwd(), 'data', 'captured_faces')
            object_dir = os.path.join(base_dir, self._sanitize_filename(object_name))
            os.makedirs(object_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = int(time.time())
            filename = f"{timestamp}_{self._sanitize_filename(object_name)}.jpg"
            filepath = os.path.join(object_dir, filename)
            
            # Convert BGR to RGB for PIL
            face_rgb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
            
            # Save face image
            pil_image = Image.fromarray(face_rgb)
            pil_image.save(filepath, 'JPEG', quality=85)
            
            self.logger.info(f"Captured face for {object_name}: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error capturing face: {e}")
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Ensure filename is not empty
        if not filename:
            filename = 'unknown'
        
        return filename
    
    def get_captured_faces_count(self, object_name: str = None) -> Dict[str, int]:
        """
        Get count of captured faces for objects.
        
        Args:
            object_name: Specific object name, or None for all objects
            
        Returns:
            Dictionary with face counts
        """
        try:
            base_dir = os.path.join(os.getcwd(), 'data', 'captured_faces')
            
            if not os.path.exists(base_dir):
                return {}
            
            counts = {}
            
            if object_name:
                # Get count for specific object
                object_dir = os.path.join(base_dir, self._sanitize_filename(object_name))
                if os.path.exists(object_dir):
                    files = [f for f in os.listdir(object_dir) 
                            if os.path.isfile(os.path.join(object_dir, f))]
                    counts[object_name] = len(files)
            else:
                # Get counts for all objects
                for item in os.listdir(base_dir):
                    object_dir = os.path.join(base_dir, item)
                    if os.path.isdir(object_dir):
                        files = [f for f in os.listdir(object_dir) 
                                if os.path.isfile(os.path.join(object_dir, f))]
                        counts[item] = len(files)
            
            return counts
            
        except Exception as e:
            self.logger.error(f"Error getting captured faces count: {e}")
            return {}
    
    def cleanup_old_captured_faces(self, days: int = 30) -> int:
        """
        Remove captured faces older than specified days.
        
        Args:
            days: Number of days to keep faces
            
        Returns:
            Number of files removed
        """
        try:
            base_dir = os.path.join(os.getcwd(), 'data', 'captured_faces')
            
            if not os.path.exists(base_dir):
                return 0
            
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            removed_count = 0
            
            for object_name in os.listdir(base_dir):
                object_dir = os.path.join(base_dir, object_name)
                if os.path.isdir(object_dir):
                    for filename in os.listdir(object_dir):
                        file_path = os.path.join(object_dir, filename)
                        if os.path.isfile(file_path):
                            # Extract timestamp from filename
                            try:
                                timestamp_str = filename.split('_')[0]
                                file_time = int(timestamp_str)
                                
                                if file_time < cutoff_time:
                                    os.remove(file_path)
                                    removed_count += 1
                                    self.logger.info(f"Removed old captured face: {file_path}")
                            except (ValueError, IndexError):
                                # If we can't parse timestamp, skip the file
                                continue
            
            # Remove empty directories
            for object_name in os.listdir(base_dir):
                object_dir = os.path.join(base_dir, object_name)
                if os.path.isdir(object_dir) and not os.listdir(object_dir):
                    os.rmdir(object_dir)
                    self.logger.info(f"Removed empty directory: {object_dir}")
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old captured faces: {e}")
            return 0


# Global dataset manager instance
dataset_manager = DatasetManager()

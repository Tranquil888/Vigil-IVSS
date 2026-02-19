#!/usr/bin/env python3
"""
Test script to verify all imports work correctly.
"""

def test_imports():
    """Test all module imports."""
    print("Testing Vigil surveillance system imports...")
    print("=" * 50)
    
    # Test core modules
    try:
        from vigil.core.exceptions import TrainingError, RecognitionError
        print("✓ Core exceptions imported successfully")
    except Exception as e:
        print(f"✗ Core exceptions import failed: {e}")
    
    try:
        from vigil.config.settings import settings
        print("✓ Settings module imported successfully")
    except Exception as e:
        print(f"✗ Settings import failed: {e}")
    
    try:
        from vigil.utils.logging_config import get_utils_logger, get_main_logger
        print("✓ Logging config imported successfully")
    except Exception as e:
        print(f"✗ Logging config import failed: {e}")
    
    try:
        from vigil.utils.dataset_manager import DatasetManager
        print("✓ Dataset manager imported successfully")
    except Exception as e:
        print(f"✗ Dataset manager import failed: {e}")
    
    # Test CV-dependent modules (may fail if packages not installed)
    try:
        from vigil.recognition.face_detector import face_detector
        print("✓ Face detector imported successfully")
    except ImportError as e:
        print(f"⚠ Face detector import failed (missing CV packages): {e}")
    except Exception as e:
        print(f"✗ Face detector import failed: {e}")
    
    try:
        from vigil.recognition.face_trainer import FaceTrainer
        print("✓ Face trainer imported successfully")
    except ImportError as e:
        print(f"⚠ Face trainer import failed (missing CV packages): {e}")
    except Exception as e:
        print(f"✗ Face trainer import failed: {e}")
    
    try:
        from vigil.recognition.training_service import training_service
        print("✓ Training service imported successfully")
    except ImportError as e:
        print(f"⚠ Training service import failed (missing CV packages): {e}")
    except Exception as e:
        print(f"✗ Training service import failed: {e}")
    
    # Test GUI modules
    try:
        from vigil.gui.main_window import MainWindow
        print("✓ Main window imported successfully")
    except ImportError as e:
        print(f"⚠ Main window import failed (missing CV packages): {e}")
    except Exception as e:
        print(f"✗ Main window import failed: {e}")
    
    try:
        from vigil.gui.dialogs.training_dialog import TrainingDialog
        print("✓ Training dialog imported successfully")
    except ImportError as e:
        print(f"⚠ Training dialog import failed (missing CV packages): {e}")
    except Exception as e:
        print(f"✗ Training dialog import failed: {e}")
    
    # Test application controller
    try:
        from vigil.core.app import app
        print("✓ Application controller imported successfully")
    except ImportError as e:
        print(f"⚠ Application import failed (missing CV packages): {e}")
    except Exception as e:
        print(f"✗ Application import failed: {e}")
    
    print("=" * 50)
    print("Import test completed!")
    
    # Check for required packages
    print("\nChecking required packages...")
    print("-" * 30)
    
    required_packages = {
        'tkinter': 'GUI framework',
        'PIL': 'Image processing',
        'numpy': 'Numerical computing',
        'cv2': 'Computer vision (OpenCV)',
        'face_recognition': 'Face recognition library'
    }
    
    missing_packages = []
    
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} - {description}")
        except ImportError:
            print(f"✗ {package} - {description} (MISSING)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠ WARNING: Missing packages: {', '.join(missing_packages)}")
        print("To install missing packages, run:")
        print("pip install opencv-python face-recognition")
    else:
        print("\n✓ All required packages are installed!")

if __name__ == "__main__":
    test_imports()

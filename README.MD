# Vigil (prev. Dozor): Intelligent Video Surveillance System

Vigil is an intelligent software solution designed for real-time video monitoring, object recognition, and event analysis. Developed using Python and Computer Vision technologies, it automates security processes by identifying faces and objects in video streams, logging events, and archiving data.

The system is designed to be a cost-effective, functional alternative to expensive enterprise security systems, making it suitable for small businesses, residential complexes, and educational institutions.

## 📋 Table of Contents
- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [License](#-license)

## 🚀 Features

### Real-Time Monitoring & Recognition
- **Video Streaming**: Streams video from IP cameras or video files
- **Face & Object Detection**: Detects and recognizes faces/objects using CNN or HOG models
- **Smart Display**: Shows recognized object names and categories (e.g., "Resident", "Guest", "Attention!")

### Event Logging & Archiving
- **Automatic Logging**: Logs events with timestamps and recognition confidence
- **Media Capture**: Saves photo and video clips of specific events
- **Searchable Journal**: Provides a searchable event log filterable by date or object

### Object Management
- **Profile Management**: Create, edit, and delete observed objects (profiles)
- **Dataset Management**: Manage photo datasets for model training directly within the interface
- **Model Training**: Train the recognition model on new data

### Security & Administration
- **Role-Based Access**: Administrator vs. Operator roles with different permissions
- **Secure Authentication**: Secure login and session management
- **Camera Configuration**: Camera connection settings and video quality adjustments

### Performance
- **Multiprocessing**: Utilizes multiprocessing for smooth UI performance while processing video
- **Hardware Acceleration**: Supports NVIDIA CUDA acceleration (Tensor Cores)

## ⚙️ System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB available space for application and data
- **GPU**: Optional - NVIDIA GPU with CUDA support for enhanced performance

### Dependencies
Core dependencies are listed in `requirements.txt`. Install using:
```bash
pip install -r requirements.txt
```

For optimal performance with face recognition, use conda environment:
```bash
conda create -n dlib-cuda python=3.8
conda activate dlib-cuda
pip install -r requirements.txt
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+ with pip
- Conda (recommended for face recognition dependencies)
- Git for cloning the repository

### Setup Steps
1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd dozor-clone
   ```

2. **Install Dependencies**:
   ```bash
   # Using pip
   pip install -r requirements.txt
   
   # Or using conda (recommended)
   conda create -n dlib-cuda python=3.8
   conda activate dlib-cuda
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   # Modular version (recommended)
   python main_new.py
   
   # Original version (legacy)
   python main.py
   ```

### First Run
1. Launch the application using `python main_new.py`
2. Create administrator account when prompted
3. Configure camera settings in the administration panel
4. Add objects/people to the recognition database

## 📖 Usage

### Basic Workflow
1. **Login**: Use administrator credentials to access the system
2. **Camera Setup**: Configure IP cameras or video sources in settings
3. **Object Management**: Add profiles for people/objects to recognize
4. **Monitoring**: Start real-time monitoring from the main dashboard
5. **Review Events**: Check the event log for recognition activities

### Key Operations
- **Add New Object**: Navigate to Object Management → Add Profile
- **Train Model**: Object Management → Train Model with new dataset
- **View Events**: Event Log → Filter by date/object type
- **Camera Settings**: Administration → Camera Configuration

## 📁 Project Structure

### Modular Architecture (New)
```
vigil/
├── __init__.py                 # Package initialization
├── core/                       # Core application components
│   ├── app.py                 # Main application controller
│   └── exceptions.py          # Custom exception classes
├── config/                     # Configuration management
│   ├── constants.py           # Application constants
│   └── settings.py            # Settings with database persistence
├── database/                   # Database layer
│   └── manager.py             # Database operations (4 databases)
├── auth/                       # Authentication & authorization
│   ├── authentication.py     # User authentication
│   └── authorization.py      # Role-based access control
├── gui/                        # Graphical user interface
│   ├── main_window.py         # Primary GUI window
│   └── dialogs/
│       └── auth_dialog.py     # Authentication dialogs
├── video/                      # Video processing
│   ├── capture.py             # Video capture from cameras/files
│   └── processing.py         # Frame processing and encoding
├── recognition/                # Face/object recognition
│   └── face_detector.py      # Face detection and recognition
├── events/                     # Event logging
│   └── logger.py             # Event logging and management
└── utils/                      # Utilities
    └── logging_config.py     # Centralized logging
```

### Legacy Structure (Original)
- **main.py**: Primary GUI application with tkinter interface (8,155 lines)
- **webstreaming.py**: Flask-based video streaming server
- **Database Layer**: SQLite databases for authentication, settings, and recognition data

### Entry Points
- **main_new.py**: New modular application (recommended)
- **main.py**: Original monolithic application (preserved for compatibility)

### Database Files
- `data/setting.db`: Application settings and configuration
- `data/authentication.db`: User authentication and roles
- `data/objects.db`: Recognition profiles and object data
- `data/camerasetting.db`: Camera configuration
- `data/events.db`: Event logging and journaling

### Configuration Files
- `requirements.txt`: Python dependencies
- `encodings.pickle`: Face recognition encodings (generated during training)
- `log.log`: Application log file

## � Recent Refactoring (2025-02-09)

The application has undergone a major refactoring to improve maintainability, testability, and extensibility:

### ✅ What Changed
- **Modular Architecture**: Transformed 8,155-line monolithic `main.py` into focused modules
- **Separation of Concerns**: Each module has a single responsibility
- **Dependency Injection**: Removed global variables, improved testability
- **Enhanced Error Handling**: Custom exceptions and structured logging
- **Database Abstraction**: Unified database management layer
- **Role-Based Security**: Comprehensive authentication and authorization system

### 🚀 Benefits
- **Maintainability**: Smaller, focused code files are easier to modify
- **Testability**: Individual modules can be unit tested independently
- **Performance**: Optimized resource management and lazy loading
- **Extensibility**: New features can be added without touching core code
- **Code Quality**: Better documentation, type hints, and error handling

### 📁 Migration Path
- **Backward Compatible**: All existing databases and settings preserved
- **Dual Entry Points**: Both modular (`main_new.py`) and original (`main.py`) available
- **Gradual Transition**: Can switch between versions during testing phase

## �👥 License

MIT License

---

**Note**: This software is intended for legitimate security and monitoring purposes. Users must comply with local laws and regulations regarding surveillance and privacy.
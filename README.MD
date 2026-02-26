# Vigil (prev. Dozor): Intelligent Video Surveillance System

Vigil is an intelligent software solution designed for real-time video monitoring, object recognition, and event analysis. Developed using Python and Computer Vision technologies, it automates security processes by identifying faces and objects in video streams, logging events, and archiving data.

The system is designed to be a cost-effective, functional alternative to expensive enterprise security systems, making it suitable for small businesses, residential complexes, and educational institutions.

## 📋 Table of Contents
- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Event Journal](#-event-journal)
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
- **Event Journal**: Advanced event session management with photo galleries and detailed object tracking

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

## � Event Journal

The Event Journal is an advanced feature that provides comprehensive event session management with photo galleries and detailed object tracking.

### 🎯 Key Features

#### Event Session Management
- **Automatic Session Grouping**: Groups recognition events into sessions based on inactivity periods
- **Configurable Inactivity Delay**: Default 10 seconds (adjustable by admin users)
- **Session Duration Tracking**: Automatically calculates and displays session durations
- **Event Descriptions**: Generates descriptive names with event counters and object counts

#### Photo Capture & Gallery
- **Automatic Face Capture**: Captures and saves face images for recognized objects (excludes 'Unknown')
- **Organized Storage**: Photos stored in `data/captured_faces/` with timestamp-based naming
- **Responsive Photo Grid**: Adapts to window size (2-8 columns based on available space)
- **Vertical Scrolling**: Smooth scrolling through all captured photos
- **Thumbnail Display**: 120x120px thumbnails with object names and timestamps

#### Event Details & Analysis
- **Event Table**: Lists all sessions with ID, start time, duration, and description
- **Object Tracking**: Detailed view of all recognized objects per event
- **Confidence Scores**: Shows recognition confidence for each object
- **Timestamp Tracking**: Precise timestamps for all recognition events

#### User Interface
- **Resizable Window**: Full window controls (minimize, maximize, close)
- **Responsive Layout**: Adapts to different screen sizes
- **Admin Controls**: Event delay settings and delete event functionality
- **Date Filtering**: Filter events by date range (feature placeholder)
- **Export Capability**: Export event data (feature placeholder)

### 🔧 Configuration

#### Event Inactivity Delay
- **Default**: 10 seconds
- **Access**: Admin users only
- **Location**: Event Journal → First row of controls
- **Purpose**: Determines when to start a new event session after inactivity

#### Photo Storage
- **Location**: `data/captured_faces/{object_name}/{timestamp}.jpg`
- **Format**: JPEG with automatic filename sanitization
- **Size**: Original capture size with face padding
- **Cleanup**: Manual management through file system

### 📱 Usage Guide

#### Accessing Event Journal
1. **Login** to the Vigil system
2. Navigate to **Events** → **View Events**
3. The Event Journal window will open with the event list

#### Viewing Event Details
1. **Select an event** from the events table
2. **View object details** in the middle panel
3. **Browse photos** in the photo gallery below
4. **Resize window** to adjust photo grid layout

#### Admin Operations
1. **Configure delay**: Set "Event Delay (s)" and click "Update"
2. **Delete events**: Select event and click "Delete Event" (admin only)
3. **Export data**: Click "Export" to save event data (admin only)

### 🎨 Responsive Photo Grid

The photo gallery automatically adapts to window size:
- **Small windows** (< 280px): 2 columns
- **Medium windows** (280-560px): 2-4 columns
- **Large windows** (560-840px): 4-6 columns
- **Extra large windows** (> 840px): 6-8 columns

Photos reorganize automatically when resizing the window, ensuring optimal visibility and no images are thrown off-screen.

### 🔐 Role-Based Access

#### Administrator Users
- **Full access** to all Event Journal features
- **Configure** event inactivity delay
- **Delete** individual events
- **Export** event data
- **View** all photos and details

#### Operator Users
- **View** events and photos
- **Browse** event details
- **No access** to admin settings
- **Cannot delete** events

### 📊 Database Schema

The Event Journal uses three main tables in `data/events.db`:

#### `event_sessions`
- `id`: Session identifier
- `start_time`: Session start timestamp
- `end_time`: Session end timestamp
- `duration`: Session duration in seconds
- `description`: Auto-generated description

#### `event_objects`
- `id`: Object record identifier
- `session_id`: Link to event session
- `object_name`: Recognized object name
- `object_type`: Object classification
- `timestamp`: Recognition timestamp
- `confidence`: Recognition confidence score

#### `event_photos`
- `id`: Photo record identifier
- `session_id`: Link to event session
- `photo_path`: File path to captured photo
- `timestamp`: Photo capture timestamp
- `object_name`: Object in the photo

## �� Project Structure

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
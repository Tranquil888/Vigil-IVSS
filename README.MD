# Vigil (prev. Dozor): Intelligent Video Surveillance System

Vigil is a comprehensive intelligent video surveillance system designed for real-time monitoring, face recognition, and event analysis. Built with Python and advanced computer vision technologies, it provides enterprise-grade security capabilities with a focus on affordability and accessibility.

The system combines real-time video processing, AI-powered recognition, comprehensive event management, and role-based security to create a complete surveillance solution suitable for businesses, educational institutions, and residential complexes.

## 📋 Table of Contents
- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Event Journal](#-event-journal)
- [Object Management](#-object-management)
- [Event Video Recording](#-event-video-recording)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [License](#-license)

## 🚀 Features

### Real-Time Monitoring & Recognition
- **Multi-Source Video**: Support for IP cameras, webcams, and video files
- **Advanced Face Recognition**: CNN-based detection with configurable confidence thresholds
- **Object Classification**: Automatic categorization (Resident, Staff, Visitor, Unknown, Vehicle, Animal, Other)
- **Smart Display**: Real-time overlay of recognition results with confidence scores
- **Performance Optimization**: Resolution-aware frame skipping and hardware acceleration support

### Event Management & Analysis
- **Intelligent Session Management**: Automatic event grouping based on configurable inactivity periods
- **Comprehensive Event Journal**: Advanced UI for browsing, filtering, and analyzing events
- **Multi-Filter Support**: Date range, object name, and object type filtering
- **Photo Capture System**: Automatic face capture for recognized objects with organized storage
- **Event Video Recording**: 10-second video clips captured at event start
- **Responsive Photo Gallery**: Dynamic grid layout (2-8 columns) with vertical scrolling

### Object Management System
- **Complete Profile Management**: Create, edit, and delete object profiles
- **Avatar Management**: Upload custom avatars or use category-based defaults
- **Dataset Management**: Integrated photo dataset management for training
- **Model Training**: On-demand face recognition model training
- **Category-Based Organization**: Automatic classification and color coding

### Security & Administration
- **Role-Based Access Control**: Administrator and Operator roles with granular permissions
- **Secure Authentication**: Encrypted login and session management
- **Admin Controls**: Event delay configuration, user management, and system settings
- **Audit Trail**: Comprehensive logging of all system activities

### Video & Media Features
- **Event Video Buffer**: Continuous 10-second circular buffer for event recording
- **Custom Video Player**: Full-featured player with speed control (0.5x-3.0x) and frame navigation
- **Video Export**: MP4 format with proper timestamps and metadata
- **Photo Management**: Automatic capture, storage, and gallery display

### Performance & Architecture
- **Modular Design**: Clean separation of concerns with focused modules
- **Multi-Processing**: Smooth UI performance during intensive video processing
- **Hardware Acceleration**: NVIDIA CUDA support with dlib integration
- **Database Abstraction**: Unified management of multiple SQLite databases
- **Error Handling**: Comprehensive exception handling and logging

## ⚙️ System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended for optimal performance
- **Storage**: 10GB available space for application, databases, and media
- **GPU**: Optional - NVIDIA GPU with CUDA support for enhanced face recognition

### Recommended Setup
- **CPU**: Multi-core processor for video processing
- **GPU**: NVIDIA GPU with CUDA cores for accelerated face recognition
- **RAM**: 8GB+ for concurrent video processing and recognition
- **Storage**: SSD for better database and video performance

### Dependencies
Core dependencies are managed through `requirements.txt`:

```bash
# Core dependencies
pip install -r requirements.txt
```

For optimal face recognition performance with CUDA acceleration:
```bash
conda create -n dlib-cuda python=3.8
conda activate dlib-cuda
pip install -r requirements.txt
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+ with pip
- Conda (recommended for face recognition with CUDA)
- Git for repository cloning
- Optional: NVIDIA GPU with CUDA drivers

### Setup Steps

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd dozor-clone
   ```

2. **Environment Setup**:
   ```bash
   # Using conda (recommended for face recognition)
   conda create -n dlib-cuda python=3.8
   conda activate dlib-cuda
   
   # Or use system Python
   python -m venv vigil-env
   source vigil-env/bin/activate  # Linux/Mac
   # vigil-env\Scripts\activate  # Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initial Setup**:
   ```bash
   python setup_admin.py  # Create initial admin account
   ```

5. **Run Application**:
   ```bash
   python main_new.py  # Modular version (recommended)
   ```

### First Run Configuration
1. Launch with `python main_new.py`
2. Create administrator account through setup wizard
3. Configure camera sources and settings
4. Add objects/people to recognition database
5. Train recognition model with initial dataset

## 📖 Usage

### Basic Workflow
1. **System Login**: Authenticate with administrator credentials
2. **Camera Configuration**: Set up video sources in administration panel
3. **Object Management**: Add profiles for people/objects to recognize
4. **Start Monitoring**: Begin real-time surveillance from main dashboard
5. **Review Events**: Analyze recognition activities through Event Journal

### Key Operations
- **Add Object**: Object Management → Add Profile (with avatar upload)
- **Train Model**: Object Management → Train Model
- **View Events**: Events → View Events (with filtering options)
- **Camera Settings**: Administration → Camera Configuration
- **User Management**: Administration → User List (admin only)

### Performance Tips
- Use CUDA-enabled environment for better face recognition speed
- Adjust confidence thresholds based on lighting conditions
- Configure appropriate inactivity delays for event grouping
- Regular maintenance of object datasets and model retraining

## 📊 Event Journal

The Event Journal provides comprehensive event session management with advanced filtering, photo galleries, and video playback capabilities.

### 🎯 Core Features

#### Event Session Management
- **Automatic Grouping**: Events grouped into sessions based on inactivity periods
- **Configurable Delays**: Default 10-second inactivity delay (admin adjustable)
- **Duration Tracking**: Real-time duration calculation and display
- **Session Descriptions**: Auto-generated descriptive names (e.g., "event00017-3-objects")

#### Advanced Filtering System
- **Date Range Filtering**: Filter events by start/end dates with YYYY-MM-DD format
- **Object Name Filtering**: Partial text matching for object names
- **Object Type Filtering**: Dropdown selection (Person, Unknown, Vehicle, Animal, Other)
- **Combined Filtering**: Apply multiple filters simultaneously
- **Real-time Results**: Immediate filtering with status feedback

#### Photo Gallery & Management
- **Automatic Capture**: Face photos captured for recognized objects (excludes 'Unknown')
- **Organized Storage**: `data/captured_faces/{object_name}/{timestamp}.jpg` structure
- **Responsive Grid**: 2-8 columns based on window size (140px minimum per photo)
- **Thumbnail Display**: 120x120px thumbnails with PIL LANCZOS resampling
- **Vertical Scrolling**: Smooth scrolling through all captured photos

#### Event Video Integration
- **10-Second Clips**: Automatic video capture at event start
- **Custom Player**: Full playback controls with speed adjustment (0.5x-3.0x)
- **Progress Bar**: Time display and frame-by-frame navigation
- **Video Status**: Dynamic button states based on video availability

### 🔧 Configuration & Access

#### Admin Controls
- **Event Delay**: Configure inactivity delay for session creation
- **Event Deletion**: Remove individual events (admin only)
- **System Settings**: Access to advanced configuration options

#### Role-Based Access
- **Administrators**: Full access to all features, configuration, and deletion
- **Operators**: View-only access to events, photos, and videos

#### Database Schema
- **event_sessions**: Session metadata (ID, timestamps, duration, description)
- **event_objects**: Recognized objects with confidence scores
- **event_photos**: Photo records with file paths and timestamps
- **event_videos**: Video metadata with file information and duration

### 📱 Usage Guide

#### Accessing Event Journal
1. Login to Vigil system
2. Navigate to **Events** → **View Events**
3. Browse events table with sorting and filtering

#### Filtering Events
1. **Date Filtering**: Enter date range in "From" and "To" fields
2. **Object Filtering**: Enter partial name in "Object Name" field
3. **Type Filtering**: Select category from "Object Type" dropdown
4. **Apply Filters**: Click "Apply Filters" for object filtering, "Filter" for date filtering

#### Viewing Event Details
1. Select event from table
2. View object details in middle panel
3. Browse photos in responsive gallery
4. Watch event video with custom player

## 👥 Object Management

The Object Management system provides comprehensive profile management with avatar support and dataset integration.

### 🎯 Features

#### Profile Management
- **Complete CRUD Operations**: Create, read, update, delete object profiles
- **Avatar System**: Upload custom avatars or use category-based defaults
- **Category Classification**: Automatic color coding (Resident-Green, Staff-Grey, Visitor-Blue, Unknown-Red)
- **Metadata Storage**: Object details, photos, and recognition encodings

#### Avatar Management
- **Custom Upload**: Support for JPG, JPEG, PNG, BMP, GIF (max 5MB)
- **Default Avatars**: Category-based default avatars with color coding
- **Unique Naming**: UUID-based file naming to prevent conflicts
- **Image Processing**: PIL LANCZOS resampling with JPEG quality 85%
- **Storage Structure**: `data/photo/objects/` with organized subdirectories

#### Dataset Integration
- **Photo Management**: Add/remove photos for object training
- **Dataset Organization**: Structured storage in `dataset/{object_name}/`
- **Training Integration**: Direct integration with face recognition training
- **Quality Control**: Image validation and processing

### 🔐 Security & Permissions

#### Admin-Only Features
- **Avatar Upload/Removal**: Only users with `can_manage_objects` permission
- **Profile Creation/Deletion**: Full CRUD access for administrators
- **Dataset Management**: Training and dataset modification capabilities

#### Operator Access
- **View Profiles**: Browse object information and photos
- **No Modifications**: Read-only access to object data

### 📁 Storage Structure

#### Avatar Storage
```
data/photo/objects/
├── no_avatar_green.jpg    (Resident - Green)
├── no_avatar_grey.jpg     (Staff - Grey)  
├── no_avatar_blue.jpg     (Visitor - Blue)
├── no_avatar_red.jpg      (Unknown - Red)
└── avatar_*.jpg           (Custom avatars - UUID named)
```

#### Dataset Storage
```
dataset/
├── {object_name}/
│   ├── photo_001.jpg
│   ├── photo_002.jpg
│   └── ...
```

## 🎥 Event Video Recording

Vigil includes automatic event video recording with continuous buffering and custom playback capabilities.

### 🎯 Features

#### Continuous Video Buffer
- **Circular Buffer**: 10-second buffer at 10 FPS continuously updated
- **Event Trigger**: Automatic video capture when recognition events occur
- **Thread-Safe Operations**: Concurrent frame feeding and video processing
- **Storage Management**: Automatic file naming and directory creation

#### Video Capture System
- **Event-Based Recording**: 10-second clips saved at event start
- **MP4 Format**: Standard MP4 with MP4V codec for compatibility
- **Metadata Storage**: Database integration with video information
- **File Organization**: `data/event_videos/event_{session_id}_{timestamp}.mp4`

#### Custom Video Player
- **Full Playback Controls**: Play/Pause, Stop, Seek functionality
- **Speed Control**: Adjustable playback speed (0.5x to 3.0x)
- **Progress Bar**: Visual progress with time display
- **Frame Navigation**: Frame-by-frame stepping capability
- **Aspect Ratio**: Proper video aspect ratio handling

### 🔧 Technical Implementation

#### Video Buffer (`vigil/video/event_buffer.py`)
- **Queue-Based Storage**: Thread-safe frame queue with configurable size
- **Background Processing**: Async video saving and database operations
- **Error Handling**: Comprehensive error recovery and logging
- **Performance Optimization**: Efficient frame management and memory usage

#### Video Player (`vigil/gui/dialogs/video_player_dialog.py`)
- **OpenCV Integration**: CV2 VideoCapture for robust video handling
- **Threading**: Separate thread for smooth playback
- **UI Controls**: Tkinter-based interface with modern styling
- **Cleanup**: Proper resource management and cleanup

#### Database Integration
- **event_videos Table**: Video metadata storage with session linking
- **Automatic Cleanup**: Video removal when events are deleted
- **Query Optimization**: Efficient video retrieval and filtering

### 📱 Usage

#### Automatic Recording
1. System continuously buffers video frames
2. Face recognition event triggers new session
3. 10-second video clip automatically saved
4. Video metadata stored in database
5. Video available in Event Journal

#### Playback
1. Open Event Journal → Select event with video
2. Click "Open Video" button
3. Use player controls for playback
4. Adjust speed with speed control
5. Navigate frames with seek bar

## 🏗️ Project Structure

Vigil uses a modular architecture with clear separation of concerns and focused modules.

### 📁 Modular Architecture
```
vigil/
├── __init__.py                 # Package initialization
├── core/                       # Core application components
│   ├── __init__.py
│   ├── app.py                 # Main application controller
│   └── exceptions.py          # Custom exception classes
├── config/                     # Configuration management
│   ├── __init__.py
│   ├── constants.py           # Application constants
│   └── settings.py            # Settings with database persistence
├── database/                   # Database layer
│   ├── __init__.py
│   ├── manager.py             # Multi-database operations
│   └── objects_manager.py     # Object-specific database operations
├── auth/                       # Authentication & authorization
│   ├── __init__.py
│   ├── authentication.py     # User authentication
│   └── authorization.py      # Role-based access control
├── gui/                        # Graphical user interface
│   ├── __init__.py
│   ├── main_window.py         # Primary GUI window
│   ├── components/            # Reusable UI components
│   │   └── __init__.py
│   └── dialogs/               # Modal dialogs
│       ├── __init__.py
│       ├── auth_dialog.py     # Authentication dialogs
│       ├── event_journal_dialog.py    # Event journal interface
│       ├── object_dialogs.py          # Object management dialogs
│       ├── video_player_dialog.py     # Video player dialog
│       ├── person_selection_dialog.py # Person selection
│       ├── photo_journal_dialog.py    # Photo gallery
│       ├── training_dialog.py         # Model training
│       └── user_list_dialog.py        # User management
├── video/                      # Video processing
│   ├── __init__.py
│   ├── capture.py             # Video capture from cameras/files
│   ├── processing.py         # Frame processing and encoding
│   └── event_buffer.py       # Event video buffering system
├── recognition/                # Face/object recognition
│   ├── __init__.py
│   ├── face_detector.py      # Face detection and recognition
│   ├── face_trainer.py        # Model training functionality
│   └── training_service.py   # Training orchestration
├── events/                     # Event management
│   ├── __init__.py
│   ├── logger.py             # Event logging
│   └── session_manager.py    # Event session management
├── services/                   # Business logic services
│   ├── __init__.py
│   └── object_service.py     # Object management service
├── models/                     # Data models
│   ├── __init__.py
│   └── object.py             # Object data model
└── utils/                      # Utilities
    ├── __init__.py
    ├── dataset_manager.py    # Dataset management utilities
    └── logging_config.py     # Centralized logging configuration
```

### 🗄️ Database Structure
Multiple SQLite databases for different concerns:
- `data/setting.db`: Application settings and configuration
- `data/authentication.db`: User authentication and role management
- `data/objects.db`: Recognition profiles and object data
- `data/camerasetting.db`: Camera configuration and settings
- `data/events.db`: Event logging, sessions, photos, and videos

### 📂 Media Storage
Organized media storage for efficient access:
- `data/captured_faces/`: Event photos organized by object
- `data/event_videos/`: Event video clips with timestamps
- `data/photo/objects/`: Object avatars and default images
- `dataset/`: Training datasets organized by object name

### 🔧 Entry Points
- `main_new.py`: Modular application (recommended)
- `main.py`: Legacy monolithic application (preserved)
- `setup_admin.py`: Initial administrator setup
- `webstreaming.py`: Flask-based web streaming server

## ⚙️ Configuration

### System Settings
Key configuration options available through the admin interface:

#### Recognition Settings
- **Confidence Threshold**: Minimum confidence for face recognition (default: 45%)
- **Inactivity Delay**: Event session grouping delay (default: 10 seconds)
- **Model Training**: On-demand training with dataset management

#### Video Settings
- **Camera Sources**: IP cameras, webcams, and video files
- **Resolution Settings**: Adaptive processing based on video resolution
- **Performance Options**: Frame skipping and hardware acceleration

#### Security Settings
- **User Management**: Role-based access control
- **Authentication**: Secure login and session management
- **Permission System**: Granular access control for features

### Environment Configuration
- **CUDA Support**: Optional GPU acceleration for face recognition
- **Logging Levels**: Configurable logging for debugging and monitoring
- **Database Paths**: Customizable storage locations

## 📜 License

MIT License - See LICENSE file for details.

---

**Important Notice**: This software is intended for legitimate security and monitoring purposes. Users must comply with all applicable local laws and regulations regarding surveillance, privacy, and data protection. The system includes privacy-enhancing features and should be used responsibly and ethically.
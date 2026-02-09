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
Core dependencies are installed automatically during setup (see Installation section).

## 🛠️ Installation

### Prerequisites

(To be configured)

### Setup Steps

(To be configured)

### First Run
1. Launch the application using `python main.py`
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

(To be configured)

### Key Modules
- **main.py**: Primary GUI application with tkinter interface
- **webstreaming.py**: Flask-based video streaming server
- **Database Layer**: SQLite databases for authentication, settings, and recognition data

## 👥 License

MIT License

---

**Note**: This software is intended for legitimate security and monitoring purposes. Users must comply with local laws and regulations regarding surveillance and privacy.
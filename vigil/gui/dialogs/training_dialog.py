"""
Training dialog for face recognition model training.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
from typing import Optional, Callable
from vigil.recognition.training_service import training_service
from vigil.utils.logging_config import get_ui_logger


class TrainingDialog:
    """Dialog for face recognition model training."""
    
    def __init__(self, parent):
        self.parent = parent
        self.logger = get_ui_logger()
        self.dialog = None
        self.progress_var = None
        self.progress_bar = None
        self.status_label = None
        self.stats_label = None
        self.start_button = None
        self.stop_button = None
        self.close_button = None
        self.dataset_path_var = None
        self.model_path_var = None
        self.algorithm_var = None
        self.tolerance_var = None
        
    def show(self) -> None:
        """Show the training dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Face Recognition Training")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self._create_widgets()
        self._load_current_settings()
        self._update_dataset_info()
        
        # Handle dialog closing
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Training Configuration", padding="10")
        config_frame.pack(fill='x', pady=(0, 10))
        
        # Dataset path
        ttk.Label(config_frame, text="Dataset Path:").grid(row=0, column=0, sticky='w', pady=2)
        self.dataset_path_var = tk.StringVar()
        dataset_frame = ttk.Frame(config_frame)
        dataset_frame.grid(row=0, column=1, columnspan=2, sticky='ew', pady=2)
        
        ttk.Entry(dataset_frame, textvariable=self.dataset_path_var, width=50).pack(side='left', fill='x', expand=True)
        ttk.Button(dataset_frame, text="Browse", command=self._browse_dataset).pack(side='right', padx=(5, 0))
        
        # Model path
        ttk.Label(config_frame, text="Model Output Path:").grid(row=1, column=0, sticky='w', pady=2)
        self.model_path_var = tk.StringVar()
        model_frame = ttk.Frame(config_frame)
        model_frame.grid(row=1, column=1, columnspan=2, sticky='ew', pady=2)
        
        ttk.Entry(model_frame, textvariable=self.model_path_var, width=50).pack(side='left', fill='x', expand=True)
        ttk.Button(model_frame, text="Browse", command=self._browse_model).pack(side='right', padx=(5, 0))
        
        # Algorithm selection
        ttk.Label(config_frame, text="Detection Algorithm:").grid(row=2, column=0, sticky='w', pady=2)
        self.algorithm_var = tk.StringVar(value="cnn")
        algorithm_frame = ttk.Frame(config_frame)
        algorithm_frame.grid(row=2, column=1, sticky='w', pady=2)
        
        ttk.Radiobutton(algorithm_frame, text="CNN (Accurate)", variable=self.algorithm_var, 
                       value="cnn").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(algorithm_frame, text="HOG (Fast)", variable=self.algorithm_var, 
                       value="hog").pack(side='left')
        
        # Tolerance
        ttk.Label(config_frame, text="Recognition Tolerance:").grid(row=3, column=0, sticky='w', pady=2)
        self.tolerance_var = tk.StringVar(value="0.6")
        tolerance_frame = ttk.Frame(config_frame)
        tolerance_frame.grid(row=3, column=1, sticky='w', pady=2)
        
        ttk.Entry(tolerance_frame, textvariable=self.tolerance_var, width=10).pack(side='left')
        ttk.Label(tolerance_frame, text="(0.0-1.0, lower = more strict)").pack(side='left', padx=(5, 0))
        
        # Configure grid weights
        config_frame.columnconfigure(1, weight=1)
        
        # Dataset info frame
        info_frame = ttk.LabelFrame(main_frame, text="Dataset Information", padding="10")
        info_frame.pack(fill='x', pady=(0, 10))
        
        self.stats_label = ttk.Label(info_frame, text="Loading dataset information...")
        self.stats_label.pack(anchor='w')
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Training Progress", padding="10")
        progress_frame.pack(fill='x', pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                        maximum=100, length=550)
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
        self.status_label = ttk.Label(progress_frame, text="Ready to start training")
        self.status_label.pack(anchor='w')
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill='x', pady=(10, 0))
        
        self.start_button = ttk.Button(buttons_frame, text="Start Training", 
                                   command=self._start_training)
        self.start_button.pack(side='left', padx=(0, 5))
        
        self.stop_button = ttk.Button(buttons_frame, text="Stop Training", 
                                  command=self._stop_training, state='disabled')
        self.stop_button.pack(side='left', padx=(0, 5))
        
        ttk.Button(buttons_frame, text="Create Dataset Structure", 
                 command=self._create_dataset_structure).pack(side='left', padx=(0, 5))
        
        ttk.Button(buttons_frame, text="Refresh Info", 
                 command=self._update_dataset_info).pack(side='left', padx=(0, 5))
        
        self.close_button = ttk.Button(buttons_frame, text="Close", command=self._on_closing)
        self.close_button.pack(side='right')
        
    def _load_current_settings(self) -> None:
        """Load current training service settings."""
        try:
            status = training_service.get_training_status()
            
            self.dataset_path_var.set(status.get('dataset_path', ''))
            self.model_path_var.set(status.get('model_path', ''))
            
            # Load algorithm and tolerance from face detector
            model_info = training_service.get_model_info()
            if model_info.get('algorithm'):
                self.algorithm_var.set(model_info['algorithm'])
            if model_info.get('tolerance'):
                self.tolerance_var.set(str(model_info['tolerance']))
                
        except Exception as e:
            self.logger.error(f"Error loading current settings: {e}")
    
    def _update_dataset_info(self) -> None:
        """Update dataset information display."""
        try:
            dataset_path = self.dataset_path_var.get()
            if not dataset_path:
                self.stats_label.config(text="No dataset path specified")
                return
            
            stats = training_service.get_dataset_statistics()
            if stats:
                info_text = f"Persons: {stats.get('total_persons', 0)} | "
                info_text += f"Images: {stats.get('valid_images', 0)} | "
                info_text += f"Size: {stats.get('total_size_mb', 0):.1f} MB"
                
                if stats.get('persons_with_images', 0) == 0:
                    info_text += " | WARNING: No valid images found!"
                elif stats.get('valid_images', 0) < 10:
                    info_text += " | WARNING: Very few images for training!"
                
                self.stats_label.config(text=info_text)
            else:
                self.stats_label.config(text="No dataset information available")
                
        except Exception as e:
            self.logger.error(f"Error updating dataset info: {e}")
            self.stats_label.config(text="Error loading dataset information")
    
    def _browse_dataset(self) -> None:
        """Browse for dataset directory."""
        path = filedialog.askdirectory(
            title="Select Dataset Directory",
            initialdir=self.dataset_path_var.get()
        )
        if path:
            self.dataset_path_var.set(path)
            self._update_dataset_info()
    
    def _browse_model(self) -> None:
        """Browse for model output file."""
        path = filedialog.asksaveasfilename(
            title="Save Model As",
            initialdir=os.path.dirname(self.model_path_var.get()),
            defaultextension=".pickle",
            filetypes=[("Pickle files", "*.pickle"), ("All files", "*.*")]
        )
        if path:
            self.model_path_var.set(path)
    
    def _validate_settings(self) -> bool:
        """Validate training settings."""
        try:
            # Check dataset path
            dataset_path = self.dataset_path_var.get()
            if not dataset_path:
                messagebox.showerror("Error", "Please specify a dataset path")
                return False
            
            if not os.path.exists(dataset_path):
                messagebox.showerror("Error", "Dataset directory does not exist")
                return False
            
            # Check model path
            model_path = self.model_path_var.get()
            if not model_path:
                messagebox.showerror("Error", "Please specify a model output path")
                return False
            
            # Check tolerance
            try:
                tolerance = float(self.tolerance_var.get())
                if not 0.0 <= tolerance <= 1.0:
                    messagebox.showerror("Error", "Tolerance must be between 0.0 and 1.0")
                    return False
            except ValueError:
                messagebox.showerror("Error", "Invalid tolerance value")
                return False
            
            # Validate dataset
            validation = training_service.validate_dataset()
            if not validation['valid']:
                errors = '\\n'.join(validation['errors'])
                messagebox.showerror("Dataset Error", f"Dataset validation failed:\\n{errors}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating settings: {e}")
            messagebox.showerror("Error", f"Validation failed: {e}")
            return False
    
    def _start_training(self) -> None:
        """Start the training process."""
        if not self._validate_settings():
            return
        
        try:
            # Update training service settings
            dataset_path = self.dataset_path_var.get()
            model_path = self.model_path_var.get()
            algorithm = self.algorithm_var.get()
            tolerance = float(self.tolerance_var.get())
            
            # Set callbacks
            training_service.set_callbacks(
                progress_callback=self._on_progress,
                completion_callback=self._on_training_complete
            )
            
            # Start training
            if training_service.start_training(dataset_path, model_path):
                # Update UI
                self.start_button.config(state='disabled')
                self.stop_button.config(state='normal')
                self.close_button.config(state='disabled')
                self.status_label.config(text="Training started...")
                
                self.logger.info(f"Training started: {dataset_path} -> {model_path}")
            else:
                messagebox.showerror("Error", "Failed to start training")
                
        except Exception as e:
            self.logger.error(f"Error starting training: {e}")
            messagebox.showerror("Error", f"Failed to start training: {e}")
    
    def _stop_training(self) -> None:
        """Stop the training process."""
        try:
            if training_service.stop_training():
                self.status_label.config(text="Training stopped")
                self.logger.info("Training stopped by user")
            else:
                messagebox.showwarning("Warning", "No training in progress")
                
        except Exception as e:
            self.logger.error(f"Error stopping training: {e}")
            messagebox.showerror("Error", f"Failed to stop training: {e}")
    
    def _on_progress(self, current: int, total: int, message: str) -> None:
        """Handle training progress updates."""
        try:
            if total > 0:
                progress = (current / total) * 100
                self.progress_var.set(progress)
            
            status_text = f"Progress: {current}/{total}"
            if message:
                status_text += f" - {message}"
            
            self.status_label.config(text=status_text)
            self.dialog.update_idletasks()
            
        except Exception as e:
            self.logger.error(f"Error updating progress: {e}")
    
    def _on_training_complete(self, result: dict) -> None:
        """Handle training completion."""
        try:
            # Update UI
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.close_button.config(state='normal')
            
            if result.get('success'):
                self.progress_var.set(100)
                
                # Show success message
                msg = f"Training completed successfully!\\n\\n"
                msg += f"Images processed: {result.get('total_images', 0)}\\n"
                msg += f"Faces found: {result.get('processed_faces', 0)}\\n"
                msg += f"Unique persons: {result.get('unique_faces', 0)}\\n"
                msg += f"Training time: {result.get('training_time', 0):.1f} seconds\\n"
                msg += f"Processing speed: {result.get('faces_per_second', 0):.1f} faces/sec"
                
                messagebox.showinfo("Training Complete", msg)
                self.status_label.config(text="Training completed successfully")
                
                # Update dataset info
                self._update_dataset_info()
                
            else:
                error_msg = result.get('error', 'Unknown error')
                messagebox.showerror("Training Failed", f"Training failed:\\n{error_msg}")
                self.status_label.config(text=f"Training failed: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error handling training completion: {e}")
            messagebox.showerror("Error", f"Error handling training completion: {e}")
    
    def _create_dataset_structure(self) -> None:
        """Create sample dataset structure."""
        try:
            dataset_path = self.dataset_path_var.get()
            if not dataset_path:
                messagebox.showerror("Error", "Please specify a dataset path first")
                return
            
            if training_service.create_dataset_structure():
                messagebox.showinfo("Success", "Dataset structure created successfully")
                self._update_dataset_info()
            else:
                messagebox.showerror("Error", "Failed to create dataset structure")
                
        except Exception as e:
            self.logger.error(f"Error creating dataset structure: {e}")
            messagebox.showerror("Error", f"Failed to create dataset structure: {e}")
    
    def _on_closing(self) -> None:
        """Handle dialog closing."""
        # Check if training is in progress
        status = training_service.get_training_status()
        if status.get('is_training'):
            if not messagebox.askokcancel("Training in Progress", 
                                        "Training is still in progress. Are you sure you want to close?"):
                return
        
        self.dialog.destroy()

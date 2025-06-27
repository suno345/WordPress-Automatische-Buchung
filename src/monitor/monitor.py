"""
Simple Monitor class for logging functionality
"""

import logging
import os
from datetime import datetime
from typing import Optional


class Monitor:
    """Simple monitoring and logging class"""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize Monitor
        
        Args:
            log_file: Path to log file. If None, logs to console only.
        """
        self.logger = logging.getLogger('SpreadsheetMonitor')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if log_file is specified
        if log_file:
            try:
                # Create log directory if it doesn't exist
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f"Warning: Could not create file handler for {log_file}: {e}")
    
    def log_error(self, message: str) -> None:
        """Log error message"""
        self.logger.error(message)
    
    def log_warning(self, message: str) -> None:
        """Log warning message"""
        self.logger.warning(message)
    
    def log_info(self, message: str) -> None:
        """Log info message"""
        self.logger.info(message)
    
    def log_debug(self, message: str) -> None:
        """Log debug message"""
        self.logger.debug(message)
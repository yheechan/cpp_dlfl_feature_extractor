from abc import ABC, abstractmethod
import os

class FileManager(ABC):
    """Abstract base class for file managers"""
    
    def initialize_working_directory_on_local(self):
        """Set up the working directory for file operations"""
        
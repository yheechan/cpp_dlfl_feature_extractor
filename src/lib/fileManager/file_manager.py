from abc import ABC, abstractmethod

from utils.file_utils import *

class FileManager(ABC):
    """Abstract base class for file managers"""

    def make_directory(self, dir_path: str):
        make_directory(dir_path)

    def remove_directory(self, dir_path: str):
        remove_directory(dir_path)
    
    def copy_directory(self, src: str, dest: str):
        copy_directory(src, dest)
    
    def copy_file(self, src: str, dest: str):
        copy_file(src, dest)
    
    def remove_file(self, file_path: str):
        remove_file(file_path)

    @abstractmethod
    def make_specific_directory(self, dir_path: str, machine: str = None):
        """Abstract method to be implemented by subclasses for making directories in a specific way"""
        raise NotImplementedError("Subclasses must implement make_specific_directory() method")
    
    @abstractmethod
    def remove_specific_directory(self, dir_path: str, machine: str = None):
        """Abstract method to be implemented by subclasses for removing directories in a specific way"""
        raise NotImplementedError("Subclasses must implement remove_specific_directory() method")
    
    @abstractmethod
    def copy_specific_directory(self, src: str, dest: str, machine: str = None):
        """Abstract method to be implemented by subclasses for copying directories in a specific way"""
        raise NotImplementedError("Subclasses must implement copy_specific_directory() method")
    
    @abstractmethod
    def copy_specific_file(self, src: str, dest: str, machine: str = None):
        """Abstract method to be implemented by subclasses for copying files in a specific way"""
        raise NotImplementedError("Subclasses must implement copy_specific_file() method")
    
    @abstractmethod
    def remove_specific_file(self, file_path: str, machine: str = None):
        """Abstract method to be implemented by subclasses for removing files in a specific way"""
        raise NotImplementedError("Subclasses must implement remove_specific_file() method")
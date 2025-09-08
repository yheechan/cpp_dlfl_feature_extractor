import logging
from typing import Dict, Type

from lib.fileManager.file_manager import FileManager
from lib.fileManager.local_file_manager import LocalFileManager
from lib.fileManager.remote_file_manager import RemoteFileManager

LOGGER = logging.getLogger(__name__)

class FileManagerFactory:
    """Factory class for creating different types of file managers"""
    
    # Registry of available file managers
    _file_managers: Dict[str, Type[FileManager]] = {
        "local": LocalFileManager,
        "remote": RemoteFileManager,
    }
    
    @classmethod
    def create_file_manager(cls, is_remote: bool) -> FileManager:
        """Create and return a file manager instance based on the specified type"""
        if is_remote:
            manager_type = "remote"
        else:
            manager_type = "local"

        if manager_type not in cls._file_managers:
            available_types = ", ".join(cls._file_managers.keys())
            error_msg = f"Unknown file manager type: {manager_type}. Available types: {available_types}"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)
        
        manager_class = cls._file_managers[manager_type]
        manager_instance = manager_class()
        LOGGER.info(f"Created file manager of type: {manager_type}")
        return manager_instance
    
    @classmethod
    def get_available_file_managers(cls) -> list:
        """Return a list of available file manager types"""
        return list(cls._file_managers.keys())
    
    @classmethod
    def register_file_manager(cls, manager_type: str, manager_class: Type[FileManager]):
        """Register a new file manager type (useful for plugins or extensions)"""
        cls._file_managers[manager_type] = manager_class
        LOGGER.info(f"Registered new file manager type: {manager_type}")

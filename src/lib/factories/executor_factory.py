import logging
from typing import Dict, Type

from lib.executor.executor import Executor
from lib.executor.local_executor import LocalExecutor
from lib.executor.remote_executor import RemoteExecutor

LOGGER = logging.getLogger(__name__)

class ExecutorFactory:
    """Factory class for creating different types of executors"""
    
    # Registry of available executors
    _executors: Dict[str, Type[Executor]] = {
        "local": LocalExecutor,
        "remote": RemoteExecutor,
        # Add more executors here as you implement them
        # "cloud": CloudExecutor,
    }
    
    @classmethod
    def create_executor(cls, is_remote: bool) -> Executor:
        """Create and return an executor instance based on the specified type"""
        if is_remote:
            executor_type = "remote"
        else:
            executor_type = "local"

        if executor_type not in cls._executors:
            available_types = ", ".join(cls._executors.keys())
            error_msg = f"Unknown executor type: {executor_type}. Available types: {available_types}"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)
        
        executor_class = cls._executors[executor_type]
        executor_instance = executor_class()
        LOGGER.info(f"Created executor of type: {executor_type}")
        return executor_instance
    
    @classmethod
    def get_available_executors(cls) -> list:
        """Return a list of available executor types"""
        return list(cls._executors.keys())
    
    @classmethod
    def register_executor(cls, executor_type: str, executor_class: Type[Executor]):
        """Register a new executor type (useful for plugins or extensions)"""
        cls._executors[executor_type] = executor_class
        LOGGER.info(f"Registered new executor type: {executor_type}")

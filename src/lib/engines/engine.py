from abc import ABC, abstractmethod


class Engine(ABC):
    def __init__(self):
        pass
    
    @abstractmethod
    def run(self):
        """Execute the engine's main functionality"""
        raise NotImplementedError("Subclasses must implement run() method")
    
    def cleanup(self):
        """Optional cleanup method that subclasses can override"""
        pass

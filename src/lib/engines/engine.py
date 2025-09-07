from abc import ABC, abstractmethod

from lib.experiment_configs import ExperimentConfigs

class Engine(ABC):
    def __init__(self, CONFIG: ExperimentConfigs):
        self.CONFIG = CONFIG

    @abstractmethod
    def run(self):
        """Execute the engine's main functionality"""
        raise NotImplementedError("Subclasses must implement run() method")
    
    def cleanup(self):
        """Optional cleanup method that subclasses can override"""
        pass

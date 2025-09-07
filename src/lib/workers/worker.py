from abc import ABC, abstractmethod

from lib.experiment_configs import ExperimentConfigs

class Worker(ABC):
    def __init__(self, configs: ExperimentConfigs):
        self.configs = configs

    @abstractmethod
    def execute(self):
        """Execute the worker's main functionality"""
        raise NotImplementedError("Subclasses must implement execute() method")

    def stop(self):
        """Optional stop method that subclasses can override"""
        pass
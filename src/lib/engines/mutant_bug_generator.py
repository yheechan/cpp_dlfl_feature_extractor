import logging

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs
from lib.factories.file_manger_factory import FileManagerFactory
from lib.subject import Subject

LOGGER = logging.getLogger(__name__)

class MutantBugGenerator(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutantBugGenerator initialized")
    
    def run(self):
        """Execute the mutant bug generation process"""
        LOGGER.info("Running Mutant Bug Generator")
        
    def cleanup(self):
        """Clean up resources used by the mutant bug generator"""
        LOGGER.info("Cleaning up MutantBugGenerator resources")
        super().cleanup()

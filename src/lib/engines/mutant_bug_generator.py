import logging

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs
from lib.factories.file_manger_factory import FileManagerFactory

LOGGER = logging.getLogger(__name__)

class MutantBugGenerator(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        self.file_manager = FileManagerFactory.create_file_manager(
            CONFIG.ARGS.is_remote
        )
        LOGGER.info("MutantBugGenerator initialized")
    
    def run(self):
        """Execute the mutant bug generation process"""
        LOGGER.info("Running Mutant Bug Generator")
        self.file_manager.initialize_working_directory_on_local(self.CONFIG)
        
    def cleanup(self):
        """Clean up resources used by the mutant bug generator"""
        LOGGER.info("Cleaning up MutantBugGenerator resources")
        super().cleanup()

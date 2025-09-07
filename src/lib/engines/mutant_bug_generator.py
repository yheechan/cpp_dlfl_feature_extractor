import logging

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs
from lib.factories.file_manger_factory import FileManagerFactory

LOGGER = logging.getLogger(__name__)

class MutantBugGenerator(Engine):
    def __init__(self, config: ExperimentConfigs):
        super().__init__(config)
        self.file_manager = FileManagerFactory.create_file_manager(
            config.ARGS.is_remote
        )
        LOGGER.info("MutantBugGenerator initialized")
    
    def run(self):
        """Execute the mutant bug generation process"""
        LOGGER.info("Running Mutant Bug Generator")
        self.file_manager.initialize_working_directory_on_local(self.config)
        # TODO: Implement your mutant bug generation logic here
        
    def cleanup(self):
        """Clean up resources used by the mutant bug generator"""
        LOGGER.info("Cleaning up MutantBugGenerator resources")
        super().cleanup()

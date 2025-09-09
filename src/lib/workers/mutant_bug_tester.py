
import logging

from lib.workers.worker import Worker
from lib.experiment_configs import ExperimentConfigs

LOGGER = logging.getLogger(__name__)

class MutantBugTester(Worker):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutantBugTester initialized")

    def execute(self):
        """Execute the mutant bug testing process"""
        LOGGER.info("Executing Mutant Bug Tester")

    def stop(self):
        """Stop the mutant bug testing process"""
        LOGGER.info("Stopping Mutant Bug Tester")
        super().stop()

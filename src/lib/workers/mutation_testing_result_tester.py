import os


from lib.workers.worker import Worker
from lib.experiment_configs import ExperimentConfigs
from lib.mutant import Mutant

from utils.command_utils import *


class MutationTestingResultTester(Worker):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutationTestingResultTester initialized")

    def execute(self):
        """Execute the mutation testing result tester"""
        LOGGER.info("Executing MutationTestingResultTester")

        self._test_mutant()
    
    def _test_mutant(self):
        LOGGER.debug(f"target_file: {self.CONFIG.ARGS.target_file}, mutant: {self.CONFIG.ARGS.mutant}")
        # set MUTANT
        MUTANT = self.make_mutant()


    def stop(self):
        """Stop the mutation testing result tester"""
        LOGGER.info("Stopping MutationTestingResultTester")
        super().stop()

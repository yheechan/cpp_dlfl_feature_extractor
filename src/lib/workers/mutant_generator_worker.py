
import os
import shutil

from lib.workers.worker import Worker
from lib.experiment_configs import ExperimentConfigs
from lib.mutant import Mutant

from utils.command_utils import *

class MutantGeneratorWorker(Worker):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutantGeneratorWorker initialized")

        self.version_coverage_dir = os.path.join(self.coverage_dir, self.CONFIG.ARGS.mutant)
        if not os.path.exists(self.version_coverage_dir):
            os.makedirs(self.version_coverage_dir, exist_ok=True)
        LOGGER.debug(f"Version coverage directory: {self.version_coverage_dir}")

        self.version_mutant_mutants_dir = os.path.join(self.mutant_mutants_dir, self.CONFIG.ARGS.mutant)

    def execute(self):
        """Execute the mutant generation process"""
        LOGGER.info("Executing Mutant Generator Worker")

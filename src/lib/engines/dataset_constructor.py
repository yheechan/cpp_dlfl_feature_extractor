import os
import logging

from src.lib.engines.engine import Engine
from src.lib.experiment_configs import ExperimentConfigs

LOGGER = logging.getLogger(__name__)

class DatasetConstructor(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        # Additional initialization for DatasetConstructor if needed

    def run(self):
        """Run the dataset construction process"""
        LOGGER.info("Running DatasetConstructor...")
        self._initialize_required_directories()

    def _initialize_basic_directory_for_machines(self):
        self.constructed_dataset_dir = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"],
            self.CONFIG.ARGS.experiment_label,
            "constructed_dataset",
            self.CONFIG.ARGS.subject
        )
        self.FILE_MANAGER.create_directory(self.constructed_dataset_dir)
        LOGGER.info(f"Constructed dataset directory initialized at {self.constructed_dataset_dir}")

    def cleanup(self):
        """Clean up resources used by the mutant dataset constructor"""
        LOGGER.info("Cleaning up DatasetConstructor resources")
        super().cleanup()

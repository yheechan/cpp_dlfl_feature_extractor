import os
import logging

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

LOGGER = logging.getLogger(__name__)

class DatasetPostprocessor(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        # Additional initialization for DatasetPostprocessor if needed
        self._initialize_required_directories()
        self.set_experiment_setup_configs()

    def run(self):
        """Run the dataset postprocessing steps"""
        LOGGER.info("Running DatasetPostprocessor...")
    
    def _initialize_required_directories(self):
        self.config_dir = os.path.join(
            self.CONFIG.ENV["ROOT_DIR"],
            "configs"
        )

        self.constructed_dataset_dir = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"],
            self.CONFIG.ARGS.experiment_label,
            "constructed_dataset"
        )

        self.posprocessed_dataset_dir = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"],
            self.CONFIG.ARGS.experiment_label,
            "postprocessed_dataset"
        )
        self.FILE_MANAGER.make_directory(self.posprocessed_dataset_dir)
        LOGGER.info(f"Constructed dataset directory initialized at {self.posprocessed_dataset_dir}")
    


import logging
import random

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class PrerequisiteDataExtractor(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("PrerequisiteDataExtractor initialized")

    def run(self):
        """Run the prerequisite data extraction process"""
        LOGGER.info("Running Prerequisite Data Extractor")

        # Initialize required tables, columns in DB
        self._initialize_required_tables()

        # Get target mutants to test
        mutant_list = self.get_target_mutants("AND initial IS TRUE AND usable IS TRUE and prerequisites IS NULL")

        if len(mutant_list) > int(self.CONFIG.ENV["NUMBER_BUGS_TO_EXTRACT_PREREQUISITES"]):
            mutant_list = random.sample(mutant_list, int(self.CONFIG.ENV["NUMBER_BUGS_TO_EXTRACT_PREREQUISITES"]))
        LOGGER.debug(f"Selected {len(mutant_list)} mutants for prerequisite data extraction")

        self._start_testing_for_prerequisite_data(mutant_list)
    
    def _initialize_required_tables(self):
        """Initialize required tables and columns in the database"""
        def _init_cpp_line_info_table():
            # Create cpp_line_info table if it doesn't exist
            if not self.DB.table_exists("cpp_line_info"):
                columns = [
                    "bug_idx INT NOT NULL", # -- Foreign key to cpp_bug_info(bug_idx)
                    "file TEXT DEFAULT NULL",
                    "function TEXT DEFAULT NULL",
                    "lineno INT DEFAULT NULL",
                    "line_idx INT",
                    "is_buggy_line BOOLEAN DEFAULT NULL",
                    "FOREIGN KEY (bug_idx) REFERENCES cpp_bug_info(bug_idx) ON DELETE CASCADE ON UPDATE CASCADE" # -- Automatically delete tc_info rows when bug_info is deleted, Update changes in bug_info to tc_info
                ]
            col_str = ", ".join(columns)
            self.DB.create_table("cpp_line_info", col_str)

            # Create a composite index on (subject, experiment_name, version)
            self.DB.create_index(
                "cpp_line_info",
                "idx_cpp_line_info_bug_idx",
                "bug_idx"
            )
        
        _init_cpp_line_info_table()
    
    def _start_testing_for_prerequisite_data(self, mutant_list: list):
        self.EXECUTOR.test_for_prerequisite_data(self.CONTEXT, mutant_list)

    
    def cleanup(self):
        """Clean up resources used by the mutant bug generator"""
        LOGGER.info("Cleaning up UsableMutantSelector resources")
        super().cleanup()

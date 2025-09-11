import logging
from pathlib import Path

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class MutantMutantGenerator(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutantMutantGenerator initialized")

    def run(self):
        """Run the mutant mutant generation process"""
        LOGGER.info("Running Mutant Mutant Generator")

        # Initialize required tables, columns in DB
        self._initialize_required_tables()

        # Get target mutants to generate mutants from
        mutant_list = self.get_target_mutants("AND initial IS TRUE AND usable IS TRUE and prerequisites IS TRUE and mbfl IS NULL")

        self._start_generating_mutants(mutant_list)
    
    def _initialize_required_tables(self):
        """Initialize required tables and columns in the database"""
        def _init_cpp_mutant_mutant_info_table():
            # Create cpp_mutant_mutant_info table if it doesn't exist
            if not self.DB.table_exists("cpp_mutant_info"):
                cols = [
                    "bug_idx INT NOT NULL", # -- Foreign key to bug_info(bug_idx)
                    "is_for_test BOOLEAN DEFAULT NULL",
                    "build_result BOOLEAN DEFAULT NULL",
                    "targetting_file TEXT",
                    "mutation_dirname TEXT",
                    "mutant_filename TEXT",
                    "mutant_idx INT",
                    "line_idx INT",
                    "mut_op TEXT",

                    "result_transition TEXT",

                    "build_time_duration FLOAT",
                    "FOREIGN KEY (bug_idx) REFERENCES cpp_bug_info(bug_idx) ON DELETE CASCADE ON UPDATE CASCADE" # -- Automatically delete tc_info rows when bug_info is deleted, Update changes in bug_info to tc_info
                ]
                col_str = ",".join(cols)
                self.DB.create_table(
                    "cpp_mutation_info",
                    columns=col_str
                )
                # Create a composite index on (subject, experiment_name, version)
                self.DB.create_index(
                    "cpp_mutation_info",
                    "idx_cpp_mutation_info_bug_idx",
                    "bug_idx"
                )
        
        _init_cpp_mutant_mutant_info_table()
    
    def _start_generating_mutants(self, mutant_list: list):
        self.EXECUTOR.generate_mutants_from_mutants(self.CONTEXT, mutant_list)

    
    def cleanup(self):
        """Clean up resources used by the mutant mutant generator"""
        LOGGER.info("Cleaning up MutantMutantGenerator resources")
        super().cleanup()
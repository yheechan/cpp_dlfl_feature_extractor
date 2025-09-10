import logging
import os
from pathlib import Path
import random

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class UsableBugSelector(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("UsableBugSelector initialized")

    def run(self):
        """Run the usable bug selection process"""
        LOGGER.info("Running Usable Bug Selector")

        # Initialize cpp_bug_info table
        self._initialize_required_tables()

        # Select bugs to check for usability
        self._check_and_mark_usable_bugs()

        # Get target mutants to check for usability
        mutants_list = self._get_target_mutants()

        self.start_testing_for_usable_bugs(mutants_list)

    def _initialize_required_tables(self):
        """Initialize required tables in the database"""
        if not self.DB.column_exists("cpp_bug_info", "initial"):
            self.DB.add_column("cpp_bug_info", "initial BOOLEAN DEFAULT NULL")
        if not self.DB.column_exists("cpp_bug_info", "usable"):
            self.DB.add_column("cpp_bug_info", "usable BOOLEAN DEFAULT NULL")
    
    def _check_and_mark_usable_bugs(self):
        bug_idx_list = self.DB.read(
            "cpp_bug_info",
            columns="bug_idx",
            conditions={
                "subject": self.CONFIG.ARGS.subject,
                "experiment_label": self.CONFIG.ARGS.experiment_label,
                "mutant_type": "appropriate_failure",
            },
            special="AND initial IS NULL AND usable IS NULL"
        )
        bug_idx_list = [row[0] for row in bug_idx_list]

        # Select N amount of buggy mutant to check for usability
        if len(bug_idx_list) > int(self.CONFIG.ENV["NUMBER_BUGS_TO_CHECK_FOR_USABILITY"]):
            bug_idx_list = random.sample(bug_idx_list, int(self.CONFIG.ENV["NUMBER_BUGS_TO_CHECK_FOR_USABILITY"]))
        
        for bug_idx in bug_idx_list:
            self.DB.update(
                "cpp_bug_info",
                set_values={"initial": True},
                conditions={"bug_idx": bug_idx}
            )

    def _get_target_mutants(self):
        self.generated_mutants_dir = os.path.join(self.out_dir, "generated_mutants")
        res = self.DB.read(
            "cpp_bug_info",
            columns="version, type, target_code_file, buggy_code_file",
            conditions={
                "subject": self.CONFIG.ARGS.subject,
                "experiment_label": self.CONFIG.ARGS.experiment_label,
            },
            special="AND initial IS TRUE AND usable IS NULL"
        )
        LOGGER.debug(f"Found {len(res)} mutants to check for usability")
        
        
        mutant_list = []
        for version, mutant_type, target_code_file, buggy_code_file in res:
            target_file_mutant_dir_name = target_code_file.replace("/", "#")
            target_file_mutant_dir_path = os.path.join(self.generated_mutants_dir, target_file_mutant_dir_name)
            mutant = Path(os.path.join(target_file_mutant_dir_path, buggy_code_file))
            mutant_list.append((target_code_file, mutant, target_file_mutant_dir_path))
        
        LOGGER.info(f"Total mutants to check for usability: {len(mutant_list)}")
        return mutant_list

    def start_testing_for_usable_bugs(self, mutant_list: list):
        self.EXECUTOR.test_for_usable_bugs(self.CONTEXT, mutant_list)
    
    def cleanup(self):
        """Clean up resources used by the mutant bug generator"""
        LOGGER.info("Cleaning up UsableMutantSelector resources")
        super().cleanup()

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

        # Select bugs to check for usability
        self._check_and_mark_usable_bugs()

        # Get target mutants to check for usability
        mutant_list = self.get_target_mutants("AND initial IS TRUE AND usable IS NULL")

        self._start_testing_for_usable_bugs(mutant_list)
    
    def _check_and_mark_usable_bugs(self):
        db_bug_idx_list = self.DB.read(
            "cpp_bug_info",
            columns="bug_idx, target_code_file, pre_start_line",
            conditions={
                "subject": self.CONFIG.ARGS.subject,
                "experiment_label": self.CONFIG.ARGS.experiment_label,
                "mutant_type": "appropriate_failure",
            },
            special="AND initial IS NULL AND usable IS NULL"
        )
        LOGGER.debug(f"There are {len(db_bug_idx_list)} bug_idx with appropriate_failure")
        file2num2bugIdx = {}
        num_files = 0
        num_lines = 0
        for bug_idx, target_code_file, pre_start_line in db_bug_idx_list:
            if target_code_file not in file2num2bugIdx:
                file2num2bugIdx[target_code_file] = {}
                num_files += 1
            if pre_start_line not in file2num2bugIdx[target_code_file]:
                file2num2bugIdx[target_code_file][pre_start_line] = []
                num_lines += 1
            file2num2bugIdx[target_code_file][pre_start_line].append(bug_idx)
        LOGGER.debug(f"There are {num_files} files, and {num_lines} lines total")
        
        selected_bug_idx_list = []
        for target_code_file, num2bugIdx in file2num2bugIdx.items():
            for num, bugIdx in num2bugIdx.items():
                selected = bugIdx.pop()
                selected_bug_idx_list.append(selected)
        
        LOGGER.debug(f"Finally selected total {len(selected_bug_idx_list)} bug_idx")



        # Select N amount of buggy mutant to check for usability
        if self.CONFIG.ARGS.subject == 'NSFW_c_msg':
            if len(selected_bug_idx_list) > int(self.CONFIG.ENV["NUMBER_BUGS_TO_CHECK_FOR_USABILITY"]):
                bug_idx_list = random.sample(selected_bug_idx_list, int(self.CONFIG.ENV["NUMBER_BUGS_TO_CHECK_FOR_USABILITY"]))
            else:
                bug_idx_list = selected_bug_idx_list
        else:
            if len(db_bug_idx_list) > int(self.CONFIG.ENV["NUMBER_BUGS_TO_CHECK_FOR_USABILITY"]):
                db_bug_idx_list = random.sample(db_bug_idx_list, int(self.CONFIG.ENV["NUMBER_BUGS_TO_CHECK_FOR_USABILITY"]))
            bug_idx_list = [row[0] for row in db_bug_idx_list]
        
        for bug_idx in bug_idx_list:
            self.DB.update(
                "cpp_bug_info",
                set_values={"initial": True},
                conditions={"bug_idx": bug_idx}
            )

        LOGGER.debug(f"UPDATED {len(bug_idx_list)} bug_idx to initial:TRUE")

    def _start_testing_for_usable_bugs(self, mutant_list: list):
        self.EXECUTOR.test_for_usable_bugs(self.CONTEXT, mutant_list)
    
    def cleanup(self):
        """Clean up resources used by the mutant bug generator"""
        LOGGER.info("Cleaning up UsableMutantSelector resources")
        super().cleanup()

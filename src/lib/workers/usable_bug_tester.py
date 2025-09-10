import os
import shutil

from lib.workers.worker import Worker
from lib.experiment_configs import ExperimentConfigs
from lib.mutant import Mutant

from utils.command_utils import *

class UsableBugTester(Worker):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("UsableBugTester initialized")

        self.version_coverage_dir = os.path.join(self.coverage_dir, self.CONFIG.ARGS.mutant)
        if not os.path.exists(self.version_coverage_dir):
            os.makedirs(self.version_coverage_dir, exist_ok=True)
        LOGGER.debug(f"Version coverage directory: {self.version_coverage_dir}")

    def execute(self):
        """Execute the usable bug testing process"""
        LOGGER.info("Executing Usable Bug Tester")

        # 1. Configure subject
        if self.CONFIG.ARGS.needs_configuration:
            LOGGER.info("Configuring subject")
            execute_bash_script(self.SUBJECT.configure_yes_cov_script, self.subject_repo)
        
        # 2. Build subject
        LOGGER.info("Building subject")
        execute_bash_script(self.SUBJECT.build_script, self.subject_repo)
        self.SUBJECT.set_environmental_variables(self.core_dir)

        # 3. Test mutant
        LOGGER.info("Testing mutants for usability")
        self.test_mutant()

        # 4. remove coverage directory
        if os.path.exists(self.version_coverage_dir):
            shutil.rmtree(self.version_coverage_dir)
            LOGGER.debug(f"Removed version coverage directory: {self.version_coverage_dir}")

    def test_mutant(self):
        LOGGER.debug(f"target_file: {self.CONFIG.ARGS.target_file}, mutant: {self.CONFIG.ARGS.mutant}")
        # set MUTANT
        MUTANT = self.make_mutant()

        # 1.1 set MUTANT basic info
        MUTANT.set_bug_idx_from_db(self.DB)
        MUTANT.set_tc_info_from_db(self.DB)
        MUTANT.set_filtered_files_for_gcovr(self.CONTEXT)

        # 2. Apply patch to taget_file
        res = MUTANT.apply_patch(revert=False)
        if not res:
            LOGGER.error(f"Failed to apply patch {MUTANT.patch_file} to {MUTANT.target_file}, skipping mutant")
            return

        # 3. Build the subject, if build fails, skip the mutant
        res = execute_bash_script(self.SUBJECT.build_script, self.subject_repo)
        if res != 0:
            LOGGER.warning(f"Build failed after applying patch {MUTANT.patch_file}, skipping mutant")
            MUTANT.apply_patch(revert=True)
            return

        # 4. run the failing test to see coverage and if it executes the failing line
        for tc_idx, tc_name in MUTANT.tc_info["fail"]:
            # 4.1 remove all gcda files
            MUTANT.remove_all_gcda()

            # 4.2 run the failing test case
            res = MUTANT.run_test_with_testScript(os.path.join(self.testcases_dir, tc_name))
            if res == 0:
                LOGGER.warning(f"Failing test case {tc_name} passed after applying mutant {MUTANT.mutant_file}, something is wrong, skipping mutant")
                MUTANT.apply_patch(revert=True)
                return

            # 4.3 remove untargeted files for gcovr
            MUTANT.remove_untargeted_files_for_gcovr(self.CONTEXT)

            # 4-4. Collect coverage
            raw_cov_file = MUTANT.generate_coverage_json(self.CONTEXT, tc_name)

            # 4-5 Check if the buggy line is coveraged
            buggy_line_covered = MUTANT.check_buggy_line_covered(
                self.CONTEXT, tc_name, raw_cov_file
            )
            if buggy_line_covered == 1:
                LOGGER.debug(f"Buggy line {MUTANT.buggy_lineno} is NOT COVERED by failing test case {tc_name}")
                MUTANT.apply_patch(revert=True)
                return
            if buggy_line_covered == -2:
                LOGGER.debug(f"File {MUTANT.target_file} is not in the coverage - target_code_file {MUTANT.target_code_file}")
                MUTANT.apply_patch(revert=True)
                return
            LOGGER.debug(f"Buggy line {MUTANT.buggy_lineno} is COVERED by failing test case {tc_name}")

        self.update_status_column_in_db(MUTANT.bug_idx, "usable")

        # 5. Revert the patch
        MUTANT.apply_patch(revert=True)

    def stop(self):
        """Stop the usable bug testing process"""
        LOGGER.info("Stopping Usable Bug Tester")
        super().stop()

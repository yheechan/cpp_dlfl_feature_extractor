import os
import shutil

from lib.workers.worker import Worker
from lib.experiment_configs import ExperimentConfigs
from lib.mutant import Mutant

from utils.command_utils import *

class PrerequisiteDataTester(Worker):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("PrerequisiteDataTester initialized")

        self.version_coverage_dir = os.path.join(self.coverage_dir, self.CONFIG.ARGS.mutant)
        if not os.path.exists(self.version_coverage_dir):
            os.makedirs(self.version_coverage_dir, exist_ok=True)
        LOGGER.debug(f"Version coverage directory: {self.version_coverage_dir}")

    def execute(self):
        """Execute the prerequisite data testing process"""
        LOGGER.info("Executing Prerequisite Data Tester")

        # 1. Configure subject
        if self.CONFIG.ARGS.needs_configuration:
            LOGGER.info("Configuring subject")
            execute_bash_script(self.SUBJECT.configure_yes_cov_script, self.SUBJECT.build_script_working_directory)
        
            # 2. Build subject
            LOGGER.info("Building subject")
            execute_bash_script(self.SUBJECT.build_script, self.SUBJECT.build_script_working_directory)
            LOGGER.debug(f"build_script_working_directory: {self.SUBJECT.build_script_working_directory}")
        self.SUBJECT.set_environmental_variables(self.core_dir)

        # 3. Test mutant
        LOGGER.info("Testing mutants for prerequisite data")
        self._test_mutant()
    
        # 4. remove coverage directory
        if os.path.exists(self.version_coverage_dir):
            shutil.rmtree(self.version_coverage_dir)
            LOGGER.debug(f"Removed version coverage directory: {self.version_coverage_dir}")
    
    def _test_mutant(self):
        LOGGER.debug(f"target_file: {self.CONFIG.ARGS.target_file}, mutant: {self.CONFIG.ARGS.mutant}")
        # set MUTANT
        MUTANT = self.make_mutant()

        # 1.1 set MUTANT basic info
        MUTANT.set_bug_idx_from_db(self.DB)
        MUTANT.set_tc_info_from_db(self.DB)

        # 1. Apply patch
        res = MUTANT.apply_patch(revert=False)
        if not res:
            LOGGER.error(f"Failed to apply patch {MUTANT.patch_file} to {MUTANT.target_file}, skipping mutant")
            return
        
        # 2. Build the subject, if build fails, skip the mutant
        res = execute_bash_script(self.CONTEXT.SUBJECT.build_script, self.CONTEXT.SUBJECT.build_script_working_directory)
        if res != 0:
            LOGGER.warning(f"Build failed after applying patch {MUTANT.patch_file}, skipping mutant")
            MUTANT.apply_patch(revert=True)
            return

        # 4. Measure coverage for candidate test cases
        res = MUTANT.measure_coverage_for_candidate_test_cases(
            self.CONTEXT, self.version_coverage_dir
        )
        if not res:
            MUTANT.apply_patch(revert=True)
            self.DB.update(
                "cpp_bug_info",
                set_values={
                    "mutant_type": "coverage_failure",
                    "prerequisites": False
                },
                conditions={"bug_idx": MUTANT.bug_idx}
            )
            LOGGER.error(f"Failed to measure coverage for mutant {MUTANT.mutant_file}, skipping mutant")
            return
        
        # 5. Update identified cctcs in DB
        MUTANT.update_cctcs_in_db(self.DB)
        MUTANT.set_tc_info_from_db(self.DB)  # refresh tc_info with using_tcs info
        if len(MUTANT.tc_info["pass"]) == 0:
            LOGGER.warning(f"Can't use this bug due to no usable passing test case for mutant {MUTANT.mutant_file}")
            MUTANT.apply_patch(revert=True)
            self.DB.update(
                "cpp_bug_info",
                set_values={
                    "mutant_type": "no_passing_tcs",
                    "prerequisites": False
                },
                conditions={"bug_idx": MUTANT.bug_idx}
            )
            return
        
        # 6. postprocess coverage info
        MUTANT.postprocess_coverage_info(self.CONTEXT, self.DB)

        # IF THERE IS NO RELEVANT PASSING TEST WE CAN'T USE THIS VERSION ANYMORE
        MUTANT.set_relevant_tc_info_from_db(self.DB)
        relevant_tc_cnt = {"fail": 0, "pass": 0}
        for tc_type in ["fail", "pass"]:
            for _, _, relevant_tc in MUTANT.tc_info_with_relevant_status[tc_type]:
                if relevant_tc == True:
                    relevant_tc_cnt[tc_type] += 1

        if relevant_tc_cnt["pass"] == 0:
            LOGGER.warning(f"Can't use this bug due to no relevant passing test case for mutant {MUTANT.mutant_file}")
            self.DB.update(
                "cpp_bug_info",
                set_values={
                    "mutant_type": "no_relevant_passing_tcs",
                    "prerequisites": False
                },
                conditions={"bug_idx": MUTANT.bug_idx}
            )
            return

        # 7. Extract stack trace for failing tests
        MUTANT.extract_stack_trace_for_failing_tests(self.CONTEXT, self.DB)

        # 8. Update bug_idx prerequisites status in DB
        self.update_status_column_in_db(MUTANT.bug_idx, "prerequisites")

        # 3. Apply revert patch
        MUTANT.apply_patch(revert=True)

    def stop(self):
        """Stop the Prerequisite Data Testing process"""
        LOGGER.info("Stopping Prerequisite Data Tester")
        super().stop()

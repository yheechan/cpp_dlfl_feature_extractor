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
            execute_bash_script(self.SUBJECT.configure_yes_cov_script, self.subject_repo)
        
        # 2. Build subject
        LOGGER.info("Building subject")
        execute_bash_script(self.SUBJECT.build_script, self.subject_repo)
        self.SUBJECT.set_environmental_variables(self.core_dir)

        # 3. Test mutant
        LOGGER.info("Testing mutants for prerequisite data")
        self._test_mutant()
    
        # # 4. remove coverage directory
        # if os.path.exists(self.version_coverage_dir):
        #     shutil.rmtree(self.version_coverage_dir)
        #     LOGGER.debug(f"Removed version coverage directory: {self.version_coverage_dir}")
    
    def _test_mutant(self):
        LOGGER.debug(f"target_file: {self.CONFIG.ARGS.target_file}, mutant: {self.CONFIG.ARGS.mutant}")
        # set MUTANT
        MUTANT = self.make_mutant()

        # 1.1 set MUTANT basic info
        MUTANT.set_bug_idx_from_db(self.DB)
        MUTANT.set_tc_info_from_db(self.DB)
        MUTANT.set_filtered_files_for_gcovr(self.CONTEXT)
        MUTANT.set_target_preprocessed_files(self.CONTEXT)

        # # 2. Extract line2function mapping
        # res = MUTANT.extract_line2function_mapping(self.CONTEXT)
        # if not res:
        #     LOGGER.error(f"Failed to extract line2function mapping for mutant {MUTANT.mutant_file}, skipping mutant")
        #     return

        # 3. Set line2function info
        MUTANT.set_line2function_info(self.CONTEXT)

        # # 4. Measure coverage for candidate test cases
        # res = MUTANT.measure_coverage_for_candidate_test_cases(self.CONTEXT)
        # if not res:
        #     LOGGER.error(f"Failed to measure coverage for mutant {MUTANT.mutant_file}, skipping mutant")
        #     return
        
        # 5. Update identified cctcs in DB
        # MUTANT.update_cctcs_in_db(self.DB)
        MUTANT.set_tc_info_from_db(self.DB)  # refresh tc_info with using_tcs info
        if len(MUTANT.tc_info["pass"]) == 0:
            LOGGER.warning(f"Can't use this bug due to no usable passing test case for mutant {MUTANT.mutant_file}")
            self.DB.update(
                "cpp_bug_info",
                set_values={"mutant_type": "no_passing_tcs"},
                conditions={"bug_idx": MUTANT.bug_idx}
            )
            return
        
        # 6. postprocess coverage info
        MUTANT.postprocess_coverage_info(self.CONTEXT, self.DB)

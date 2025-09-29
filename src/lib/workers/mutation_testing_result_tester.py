import os
import time

from lib.workers.worker import Worker
from lib.experiment_configs import ExperimentConfigs
from lib.mutant import Mutant

from utils.command_utils import *


class MutationTestingResultTester(Worker):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutationTestingResultTester initialized")

    def execute(self):
        """Execute the mutation testing result tester"""
        LOGGER.info("Executing MutationTestingResultTester")

        # 1. Configure subject
        if self.CONFIG.ARGS.needs_configuration:
            LOGGER.info("Configuring subject")
            execute_bash_script(self.SUBJECT.configure_no_cov_script, self.SUBJECT.build_script_working_directory)

            # 2. Build subject
            LOGGER.info("Building subject")
            execute_bash_script(self.SUBJECT.build_script, self.SUBJECT.build_script_working_directory)
        
        self._test_mutant()
    
    def _test_mutant(self):
        LOGGER.debug(f"target_file: {self.CONFIG.ARGS.target_file}, mutant: {self.CONFIG.ARGS.mutant}")
        # set MUTANT
        MUTANT = self.make_mutant()

        # 1 set MUTANT basic info
        MUTANT.set_bug_idx_with_specific_mutant_name_from_db(self.DB, self.CONFIG.ARGS.origin_mutant)
        MUTANT.set_relevant_tc_info_as_sorted_list_from_db(self.DB)

        # 2. Apply patch of original mutant code
        res = MUTANT.apply_patch_og(revert=False)
        if not res:
            LOGGER.error(f"Failed to apply ORIGIN patch {MUTANT.patch_file} to {MUTANT.target_file}, skipping mutant")
            return

        # 2. Apply patch to taget_file
        res = MUTANT.apply_patch(revert=False)
        if not res:
            LOGGER.error(f"Failed to apply patch {MUTANT.patch_file} to {MUTANT.target_file}, skipping mutant")
            return
        
        # 3. Build the subject, if build fails, skip the mutant
        build_start_time = time.time()
        res = execute_bash_script(self.SUBJECT.build_script, self.SUBJECT.build_script_working_directory)
        build_time_duration = ((time.time() - build_start_time) * 1000)
        if res != 0:
            LOGGER.error(f"Build failed after applying patch {MUTANT.patch_file} to {MUTANT.target_file}, skipping mutant")
            MUTANT.apply_patch(revert=True)
            MUTANT.apply_patch_og(revert=True)
            self.DB.update(
                "cpp_mutation_info",
                set_values={"build_result": False},
                conditions={
                    "bug_idx": MUTANT.bug_idx,
                    "mutant_idx": self.CONFIG.ARGS.mutant_id,
                    "mutant_filename": self.CONFIG.ARGS.mutant
                }
            )
            return
        
        result_transition = ["0"] * len(MUTANT.tc_list)
        LOGGER.debug(f"FOUND {len(MUTANT.tc_list)} tc_list")
        # 4. Run the relevant test cases
        relevant_tcs_cnt = 0
        for tc_idx, tc_name, tc_result, relevant_status in MUTANT.tc_list:
            if relevant_status == False:
                continue
            relevant_tcs_cnt += 1

            # 4.1 run the test case
            res = MUTANT.run_test_with_testScript(os.path.join(self.testcases_dir, tc_name))

            # 4.2 check the result transition
            if tc_result == "fail" and res == 0: # res == 0 means pass
                result_transition[tc_idx] = "1"
            elif tc_result == "pass" and res != 0: # res != 0 means fail
                result_transition[tc_idx] = "1"
        LOGGER.debug(f"EXECUTED {relevant_tcs_cnt} relevant tcs")
            
        # 5. Update the result transition in the database
        self.DB.update(
            "cpp_mutation_info",
            set_values={
                "result_transition": "".join(result_transition),
                "build_result": True,
                "build_time_duration": build_time_duration
            },
            conditions={
                "bug_idx": MUTANT.bug_idx,
                "mutant_idx": self.CONFIG.ARGS.mutant_id,
                "mutant_filename": self.CONFIG.ARGS.mutant
            }
        )

        # Update usable status in DB
        self.update_status_column_in_db(MUTANT.bug_idx, "mbfl")

        # REVERT after completion
        MUTANT.apply_patch(revert=True)
        MUTANT.apply_patch_og(revert=True)


    def stop(self):
        """Stop the mutation testing result tester"""
        LOGGER.info("Stopping MutationTestingResultTester")
        super().stop()

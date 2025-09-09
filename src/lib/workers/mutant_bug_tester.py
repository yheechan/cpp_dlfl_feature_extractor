import time
import logging
from pathlib import Path

from lib.workers.worker import Worker
from lib.experiment_configs import ExperimentConfigs
from lib.mutant import Mutant

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

crash_codes = [
    132,  # SIGILL
    133,  # SIGTRAP
    134,  # SIGABRT
    135,  # SIGBUS
    136,  # SIGFPE
    137,  # SIGKILL
    138,  # SIGBUS
    139,  # segfault
    140,  # SIGPIPE
    141,  # SIGALRM
    124,  # timeout
    143,  # SIGTERM
    129,  # SIGHUP
]

class MutantBugTester(Worker):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutantBugTester initialized")

    def execute(self):
        """Execute the mutant bug testing process"""
        LOGGER.info("Executing Mutant Bug Tester")

        # 1. Configure subject
        if self.CONFIG.ARGS.needs_configuration:
            LOGGER.info("Configuring subject")
            execute_bash_script(self.SUBJECT.clean_script, self.subject_repo)
            execute_bash_script(self.SUBJECT.configure_no_cov_script, self.subject_repo)
        
        # 2. Build subject
        LOGGER.info("Building subject")
        execute_bash_script(self.SUBJECT.build_script, self.subject_repo)
        self.SUBJECT.set_environmental_variables(self.core_dir)

        # 3. Test mutant
        LOGGER.info("Testing mutants")
        self.test_mutant()

    def test_mutant(self):
        target_file = os.path.join(self.core_dir, self.CONFIG.ARGS.target_file)
        if not os.path.exists(target_file):
            LOGGER.error(f"Target file {target_file} does not exist")
            return
        
        mutant_file = os.path.join(self.core_dir, f"{self.CONFIG.STAGE}-assigned_works", self.CONFIG.ARGS.mutant)
        if not os.path.exists(mutant_file):
            LOGGER.error(f"Mutant file {mutant_file} does not exist")
            return
        
        
        # 1. Patch target_file with mutant_file
        patch_file = os.path.join(self.patch_dir, f"{self.CONFIG.ARGS.mutant}.patch")
        MUTANT = Mutant(target_file, mutant_file, patch_file)

        res = MUTANT.make_path_file()
        if not res:
            LOGGER.error(f"Failed to create patch file {patch_file}, skipping mutant")
            return
        LOGGER.info(f"Patch file created at {patch_file}")


        # 2. Apply patch to taget_file
        res = MUTANT.apply_patch(revert=False)
        if not res:
            LOGGER.error(f"Failed to apply patch {patch_file} to {target_file}, skipping mutant")
            MUTANT.mutant_type = "patch_failure"
            MUTANT.apply_patch(revert=True)
            self.save_mutant(MUTANT, None)
            return

        # 3. Build the subject, if build fails, skip the mutant
        res = execute_bash_script(self.SUBJECT.build_script, self.subject_repo)
        test_results = None
        if res != 0:
            LOGGER.warning(f"Build failed after applying mutant {self.CONFIG.ARGS.mutant}, skipping")
            MUTANT.mutant_type = "build_failure"
        else:
            # 4. run the test suite
            test_results = self.run_testSuite(MUTANT)

            # 5. Don't save the mutant if all test cases pass
            if len(test_results["fail"]) == 0:
                LOGGER.info(f"Mutant {self.CONFIG.ARGS.mutant} is not killed by any test case, skipping")
                MUTANT.mutant_type = "no_failure"
            # 6. Don't save the mutant if all test cases fail
            elif len(test_results["pass"]) == 0:
                LOGGER.info(f"Mutant {self.CONFIG.ARGS.mutant} killed all test cases, skipping")
                MUTANT.mutant_type = "all_failure"
            else:
                MUTANT.mutant_type = "appropriate_failure"
            
        # 7. Save the mutant if it kills some test cases but not all
        self.save_mutant(MUTANT, test_results)

        # 8. Revert the patch
        MUTANT.apply_patch(revert=True)
    
    def run_testSuite(self, MUTANT: Mutant):
        test_results = {
            "pass": [],
            "fail": [],
            "crashed": []
        }
        for tc_script in Path(self.testcases_dir).iterdir():
            start_time = time.time()
            res = MUTANT.run_test_with_testScript(tc_script)
            end_time = time.time()
            time_duration_ms = ((end_time - start_time) * 1000)
            if res in crash_codes:
                test_results["crashed"].append((tc_script, tc_script.name, res, time_duration_ms))
            elif res == 0:
                test_results["pass"].append((tc_script, tc_script.name, res, time_duration_ms))
            elif res == 1:
                test_results["fail"].append((tc_script, tc_script.name, res, time_duration_ms))
        return test_results

    def save_mutant(self, MUTANT: Mutant, test_results: dict = None):
        def _save_mutant_info():
            cols = [
                "subject", "experiment_label", "version",
                "type", "mutant_type", "target_code_file", "buggy_code_file",
            ]
            col_str = ", ".join(cols)
            values = [
                self.CONFIG.ARGS.subject, self.CONFIG.ARGS.experiment_label, MUTANT.mutant_name,
                "mutant", MUTANT.mutant_type, MUTANT.target_file, MUTANT.mutant_file,
            ]
            self.DB.insert(
                "cpp_bug_info",
                col_str,
                values
            )
        
        def _save_test_results(bug_idx: int):
            if test_results is None:
                return
            
            tc_idx = -1
            for status in ["fail", "pass", "crashed"]:
                for tc_script, tc_name, res, time_duration_ms in test_results[status]:
                    tc_idx += 1
                    cols = [
                        "bug_idx", "tc_idx", "tc_name",
                        "tc_result", "tc_ret_code", "execution_time_ms"
                    ]
                    col_str = ", ".join(cols)
                    values = [
                        bug_idx, tc_idx, tc_name,
                        status, res, time_duration_ms
                    ]
                    self.DB.insert(
                        "cpp_tc_info",
                        col_str,
                        values
                    )
        
        _save_mutant_info()
        bug_idx = self.DB.read(
            "cpp_bug_info",
            columns="bug_idx",
            conditions={
                "subject": self.CONFIG.ARGS.subject,
                "experiment_label": self.CONFIG.ARGS.experiment_label,
                "version": MUTANT.mutant_name
            }
        )
        bug_idx = bug_idx[0][0]
        _save_test_results(bug_idx)


    def stop(self):
        """Stop the mutant bug testing process"""
        LOGGER.info("Stopping Mutant Bug Tester")
        super().stop()

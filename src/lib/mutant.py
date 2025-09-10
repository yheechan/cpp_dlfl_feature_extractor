import subprocess as sp
import os
import logging
import json

from lib.subject import Subject
from lib.database import CRUD

LOGGER = logging.getLogger(__name__)


class Mutant:
    def __init__(self,
                    subject: str = None, experiment_label: str = None,
                    target_file: str = None, target_file_path: str = None,
                    mutant_file: str = None, mutant_file_path: str = None,
                    patch_file: str = None, repo_dir: str = None):
        self.subject = subject
        self.experiment_label = experiment_label
        self.target_file = target_file
        self.target_file_path = target_file_path
        self.mutant_file = mutant_file
        self.mutant_file_path = mutant_file_path
        self.patch_file = patch_file
        self.mutant_name = os.path.basename(mutant_file)
        self.mutant_type = None
        self.repo_dir = repo_dir
        self.core_dir = os.path.dirname(self.repo_dir)

        self.bug_idx = None
        self.tc_info = {"fail": [], "pass": [], "crashed": []}

    def make_path_file(self):
        cmd = ["diff", self.target_file_path, self.mutant_file_path]
        try:
            res = sp.run(cmd, stdout=open(self.patch_file, 'w'))
            if res.returncode not in [0, 1]:  # diff returns 0 if no differences, 1 if differences found
                LOGGER.error(f"Error creating patch file with command: {' '.join(cmd)}")
                return False
            return True
        except Exception as e:
            LOGGER.error(f"Error executing command: {' '.join(cmd)}")
            raise e

    def apply_patch(self, revert=False):
        if revert:
            cmd = ["patch", "-R", "-i", self.patch_file, self.target_file_path]
        else:
            cmd = ["patch", "-i", self.patch_file, self.target_file_path]

        try:
            res = sp.run(cmd, stdout=sp.DEVNULL, stderr=sp.PIPE)
            if res.returncode != 0:
                LOGGER.error(f"Error applying patch with command: {' '.join(cmd)}")
                LOGGER.error(f"Error output: {res.stderr.decode().strip()}")
                return False
            LOGGER.debug(f"Patch applied successfully with command: {' '.join(cmd)}")
            return True
        except Exception as e:
            LOGGER.error(f"Exception occurred while applying patch with command: {' '.join(cmd)}")
            raise e

    def run_test_with_testScript(self, tc_script: str):
        tc_dir = os.path.dirname(tc_script)
        tc_name = os.path.basename(tc_script)
        res = sp.run(
            f"./{tc_name}",
            shell=True, cwd=tc_dir,
            stderr=sp.DEVNULL, stdout=sp.DEVNULL,
            env=os.environ
        )
        if res.returncode == 0:
            LOGGER.info(f"Test case {tc_name} passed")
        elif res.returncode == 1:
            LOGGER.info(f"Test case {tc_name} failed")
        else:
            LOGGER.info(f"Test case {tc_name} crashed with return code {res.returncode}")
        return res.returncode

    def set_bug_idx_from_db(self, DB: CRUD):
        bug_info = DB.read(
            "cpp_bug_info",
            columns="bug_idx, target_code_file, buggy_code_file, pre_start_line",
            conditions={
                "subject": self.subject,
                "experiment_label": self.experiment_label,
                "version": self.mutant_name,
            }
        )
        if len(bug_info) == 0:
            LOGGER.error(f"No bug info found in DB for mutant {self.mutant_name}")
            raise ValueError(f"No bug info found in DB for mutant {self.mutant_name}")
        self.bug_idx = bug_info[0][0]
        self.target_code_file = bug_info[0][1]
        self.buggy_code_filename = bug_info[0][2]
        self.buggy_lineno = str(bug_info[0][3])
        LOGGER.debug(f"Mutant {self.mutant_name} has bug_idx {self.bug_idx}")

    def set_tc_info_from_db(self, DB: CRUD):
        tc_info = DB.read(
            "cpp_tc_info",
            columns="tc_name, tc_result, tc_idx",
            conditions={"bug_idx": self.bug_idx}
        )
        for tc_name, tc_result, tc_idx in tc_info:
            if tc_result == "fail":
                self.tc_info["fail"].append((tc_idx, tc_name))
            elif tc_result == "pass":
                self.tc_info["pass"].append((tc_idx, tc_name))
            elif tc_result == "crashed":
                self.tc_info["crashed"].append((tc_idx, tc_name))
        
        LOGGER.debug(f"Mutant {self.mutant_name} has {len(self.tc_info['fail'])} failing, {len(self.tc_info['pass'])} passing, and {len(self.tc_info['crashed'])} crashed test cases")

    def remove_all_gcda(self):
        cmd = [
            "find", ".", "-type", "f",
            "-name", "*.gcda", "-delete"
        ]
        sp.check_call(cmd, cwd=self.repo_dir, stderr=sp.PIPE, stdout=sp.PIPE)
    
    def set_filtered_files_for_gcovr(self, SUBJECT: Subject, subject_lang: str = None):
        self.targeted_files = SUBJECT.subject_configs["target_files"]
        filtered_targeted_files = [os.path.join(self.core_dir, f) for f in self.targeted_files]
        self.filtered_files = "|".join(filtered_targeted_files) + "$"

        self.target_gcno_gcda = []
        for target_file in self.targeted_files:
            target_file = target_file.split("/")[-1]
            if "uriparser" in self.subject or "zlib_ng" in self.subject: # uriparser's gcno and gcda files include .c extension
                filename = target_file
            elif subject_lang == "c":
                # get filename without extension
                # remember the filename can be x.y.cpp
                filename = ".".join(target_file.split(".")[:-1])
            else:
                filename = ".".join(target_file.split(".")[:-1]) + ".cpp"
            gcno_file = "*" + filename + ".gcno"
            gcda_file = "*" + filename + ".gcda"
            self.target_gcno_gcda.append(gcno_file)
            self.target_gcno_gcda.append(gcda_file)

    def remove_untargeted_files_for_gcovr(self, repo_dir: str):
        cmd = [
            "find", ".", "-type", "f",
            "(", "-name", "*.gcno", "-o", "-name", "*.gcda", ")"
        ]

        for target_file in self.target_gcno_gcda:
            cmd.extend(["!", "-name", target_file])
        cmd.extend(["-delete"])
        sp.check_call(cmd, cwd=repo_dir, stderr=sp.PIPE, stdout=sp.PIPE)

    def generate_coverage_json(self, SUBJECT: Subject, GCOV_INFO, cov_dir, tc_script_name):
        tc_name = tc_script_name.split(".")[0]
        file_name = f"{tc_name}.raw.json"
        raw_cov_file = os.path.join(cov_dir, file_name)
        cmd = [GCOV_INFO["exec"]]
        if SUBJECT.subject_configs["cov_compiled_with_clang"] == True:
            cmd.extend(["--gcov-executable", "llvm-cov gcov"])
            cov_cwd=self.repo_dir
        else:
            obj_dir = os.path.join(self.core_dir, SUBJECT.subject_configs["gcovr_object_root"])
            src_root_dir = os.path.join(self.core_dir, SUBJECT.subject_configs["gcovr_source_root"])
            if float(GCOV_INFO["version"]) < 7.2:
                cmd.extend([
                    "--object-directory", obj_dir.__str__(),
                    "--root", src_root_dir.__str__(),
                ])
            else:
                cmd.extend([
                    "--gcov-object-directory", obj_dir.__str__(),
                    "--root", src_root_dir.__str__(),
                ])
            cov_cwd=obj_dir
        cmd.extend([
            "--filter", self.filtered_files,
            "--json", "-o", raw_cov_file.__str__(),
            "--gcov-ignore-parse",
            "--gcov-ignore-errors=no_working_dir_found"
        ])
        sp.check_call(cmd, cwd=cov_cwd, stderr=sp.PIPE, stdout=sp.PIPE)
        return raw_cov_file

    def check_buggy_line_covered(self, SUBJECT: Subject,
                                 tc_script_name, raw_cov_file):
        """
        Return 0 if the buggy line is covered
        """
        with open(raw_cov_file, 'r') as f:
            cov_data = json.load(f)
        
        # This was include because in case of libxml2
        # gcovr makes target files as <target-file>.c
        # instead of libxml2/<target-file>.c 2024-12-18
        model_file = cov_data["files"][0]["file"]
        if len(model_file.split("/")) == 1:
            target_file = self.target_file.split("/")[-1]
        elif not "zlib_ng" in self.subject and SUBJECT.subject_configs["cov_compiled_with_clang"] == False:
            target_file = self.target_file
        else:
            target_file = "/".join(self.target_file.split("/")[1:])

        file_exists = False
        for file in cov_data["files"]:
            if target_file in file["file"]:
                file_exists = True
                break
        
        if not file_exists:
            return -2
        
        for file in cov_data["files"]:
            # filename = file["file"].split("/")[-1]
            # if filename == target_file:
            filename = file["file"]
            if target_file == filename:
                lines = file["lines"]
                for line in lines:
                    if line["line_number"] == int(self.buggy_lineno):
                        cur_lineno = line["line_number"]
                        cur_count = line["count"]
                        print(f"{tc_script_name} on line {cur_lineno} has count: {cur_count}")
                        if line["count"] > 0:
                            return 0
                        else:
                            return 1
                return 1
        return 1


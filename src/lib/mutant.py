import subprocess as sp
import os
import logging
import json

from lib.database import CRUD
from lib.worker_context import WorkerContext

from utils.command_utils import *
from utils.gdb_utils import *
from utils.bitwise_utils import *

LOGGER = logging.getLogger(__name__)


class Mutant:
    def __init__(self,
                    subject: str = None, experiment_label: str = None,
                    target_file: str = None, target_file_path: str = None,
                    mutant_file: str = None, mutant_file_path: str = None,
                    patch_file: str = None, repo_dir: str = None,
                    origin_mutant_target_file = None,
                    origin_mutant_target_file_path = None,
                    origin_mutant_file = None,
                    origin_mutant_file_path = None,
                    origin_patch_file = None
                    ):
        LOGGER.info("Mutant initialized")
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

        self.origin_mutant_target_file = origin_mutant_target_file
        self.origin_mutant_target_file_path = origin_mutant_target_file_path
        self.origin_mutant_file = origin_mutant_file
        self.origin_mutant_file_path = origin_mutant_file_path
        self.origin_patch_file = origin_patch_file

        self.bug_idx = None
        self.tc_info = {"fail": [], "pass": [], "crashed": [], "cctc": []}

    def make_patch_file(self):
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
    
    def make_patch_file_og(self):
        cmd = ["diff", self.origin_mutant_target_file_path, self.origin_mutant_file_path]
        try:
            res = sp.run(cmd, stdout=open(self.origin_patch_file, 'w'))
            if res.returncode not in [0, 1]:  # diff returns 0 if no differences, 1 if differences found
                LOGGER.error(f"Error creating origin patch file with command: {' '.join(cmd)}")
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
    
    def apply_patch_og(self, revert=False):
        if revert:
            cmd = ["patch", "-R", "-i", self.origin_patch_file, self.origin_mutant_target_file_path]
        else:
            cmd = ["patch", "-i", self.origin_patch_file, self.origin_mutant_target_file_path]

        try:
            res = sp.run(cmd, stdout=sp.DEVNULL, stderr=sp.PIPE)
            if res.returncode != 0:
                LOGGER.error(f"Error applying ORIGIN patch with command: {' '.join(cmd)}")
                LOGGER.error(f"Error output: {res.stderr.decode().strip()}")
                return False
            LOGGER.debug(f"ORIGN Patch applied successfully with command: {' '.join(cmd)}")
            return True
        except Exception as e:
            LOGGER.error(f"Exception occurred while applying ORIGIN patch with command: {' '.join(cmd)}")
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
    
    def set_bug_idx_with_specific_mutant_name_from_db(self, DB: CRUD, mutant_name: str):
        bug_info = DB.read(
            "cpp_bug_info",
            columns="bug_idx, target_code_file, buggy_code_file, pre_start_line",
            conditions={
                "subject": self.subject,
                "experiment_label": self.experiment_label,
                "version": mutant_name,
            }
        )
        if len(bug_info) == 0:
            LOGGER.error(f"No bug info found in DB for mutant {mutant_name}")
            raise ValueError(f"No bug info found in DB for mutant {mutant_name}")
        self.bug_idx = bug_info[0][0]
        self.target_code_file = bug_info[0][1]
        self.buggy_code_filename = bug_info[0][2]
        
        self.buggy_lineno = str(bug_info[0][3])
        LOGGER.debug(f"Mutant {mutant_name} has bug_idx {self.bug_idx}")

    def set_tc_info_from_db(self, DB: CRUD):
        tc_info = DB.read(
            "cpp_tc_info",
            columns="tc_name, tc_result, tc_idx",
            conditions={"bug_idx": self.bug_idx}
        )
        self.tc_info = {"fail": [], "pass": [], "crashed": [], "cctc": []}
        for tc_name, tc_result, tc_idx in tc_info:
            if tc_result == "fail":
                self.tc_info["fail"].append((tc_idx, tc_name))
            elif tc_result == "pass":
                self.tc_info["pass"].append((tc_idx, tc_name))
            elif tc_result == "crashed":
                self.tc_info["crashed"].append((tc_idx, tc_name))
            elif tc_result == "cctc":
                self.tc_info["cctc"].append((tc_idx, tc_name))

        LOGGER.debug(f"failing test cases: {len(self.tc_info['fail'])}")
        LOGGER.debug(f"passing test cases: {len(self.tc_info['pass'])}")
        LOGGER.debug(f"crashed test cases: {len(self.tc_info['crashed'])}")
        LOGGER.debug(f"cctc test cases: {len(self.tc_info['cctc'])}")
    
    def set_relevant_tc_info_from_db(self, DB: CRUD):
        tc_info = DB.read(
            "cpp_tc_info",
            columns="tc_name, tc_result, tc_idx, relevant_tcs",
            conditions={"bug_idx": self.bug_idx}
        )
        self.tc_info_with_relevant_status = {"fail": [], "pass": [], "crashed": [], "cctc": []}
        for tc_name, tc_result, tc_idx, relevant_tcs in tc_info:
            if tc_result == "fail":
                self.tc_info_with_relevant_status["fail"].append((tc_idx, tc_name, relevant_tcs))
            elif tc_result == "pass":
                self.tc_info_with_relevant_status["pass"].append((tc_idx, tc_name, relevant_tcs))
            elif tc_result == "crashed":
                self.tc_info_with_relevant_status["crashed"].append((tc_idx, tc_name, relevant_tcs))
            elif tc_result == "cctc":
                self.tc_info_with_relevant_status["cctc"].append((tc_idx, tc_name, relevant_tcs))

        LOGGER.debug(f"failing test cases: {len(self.tc_info_with_relevant_status['fail'])}")
        LOGGER.debug(f"passing test cases: {len(self.tc_info_with_relevant_status['pass'])}")
        LOGGER.debug(f"crashed test cases: {len(self.tc_info_with_relevant_status['crashed'])}")
        LOGGER.debug(f"cctc test cases: {len(self.tc_info_with_relevant_status['cctc'])}")
    
    def set_relevant_tc_info_as_sorted_list_from_db(self, DB: CRUD) -> list:
        tc_info = DB.read(
            "cpp_tc_info",
            columns="tc_name, tc_result, tc_idx, relevant_tcs",
            conditions={"bug_idx": self.bug_idx},
            special="AND tc_idx != -1"
        )
        tc_list = []
        for tc_name, tc_result, tc_idx, relevant_tcs in tc_info:
            tc_list.append((tc_idx, tc_name, tc_result, relevant_tcs))
        LOGGER.debug(f"relevant test cases: {len(tc_list)}")
        tc_list.sort(key=lambda x: x[0])
        self.tc_list = tc_list


    def set_line_info_from_db(self, DB: CRUD):
        line_info = DB.read(
            "cpp_line_info",
            columns="line_idx, file, function, lineno",
            conditions={"bug_idx": self.bug_idx}
        )

        lineIdx2lineKey = {}
        filename2lineNum2lineIdx = {}
        for line_idx, filename, function_name, lineno in line_info:
            lineIdx2lineKey[line_idx] = {
                "file": filename,
                "function": function_name,
                "lineno": lineno
            }

            if filename not in filename2lineNum2lineIdx:
                filename2lineNum2lineIdx[filename] = {}
            filename2lineNum2lineIdx[filename][int(lineno)] = line_idx

        self.lineIdx2lineKey = lineIdx2lineKey
        self.filename2lineNum2lineIdx = filename2lineNum2lineIdx

    def remove_all_gcda(self):
        cmd = [
            "find", ".", "-type", "f",
            "-name", "*.gcda", "-delete"
        ]
        sp.check_call(cmd, cwd=self.repo_dir, stderr=sp.PIPE, stdout=sp.PIPE)

    def set_filtered_files_for_gcovr(self, CONTEXT: WorkerContext):
        self.targeted_files = CONTEXT.SUBJECT.subject_configs["target_files"]
        filtered_targeted_files = [os.path.join(self.core_dir, f) for f in self.targeted_files]
        self.filtered_files = "|".join(filtered_targeted_files) + "$"

        self.target_gcno_gcda = []
        for target_file in self.targeted_files:
            target_file = target_file.split("/")[-1]
            if "uriparser" in self.subject or "zlib_ng" in self.subject: # uriparser's gcno and gcda files include .c extension
                filename = target_file
            elif CONTEXT.SUBJECT.subject_configs["subject_language"] == "C":
                # get filename without extension
                # remember the filename can be x.y.cpp
                filename = ".".join(target_file.split(".")[:-1])
            else:
                filename = ".".join(target_file.split(".")[:-1]) + ".cpp"
            gcno_file = "*" + filename + ".gcno"
            gcda_file = "*" + filename + ".gcda"
            self.target_gcno_gcda.append(gcno_file)
            self.target_gcno_gcda.append(gcda_file)

    def remove_untargeted_files_for_gcovr(self, CONTEXT: WorkerContext):
        cmd = [
            "find", ".", "-type", "f",
            "(", "-name", "*.gcno", "-o", "-name", "*.gcda", ")"
        ]

        for target_file in self.target_gcno_gcda:
            cmd.extend(["!", "-name", target_file])
        cmd.extend(["-delete"])
        sp.check_call(cmd, cwd=CONTEXT.subject_repo, stderr=sp.PIPE, stdout=sp.PIPE)

    def generate_coverage_json(self, CONTEXT: WorkerContext, tc_script_name: str) -> str:
        tc_name = tc_script_name.split(".")[0]
        file_name = f"{tc_name}.raw.json"
        raw_cov_file = os.path.join(CONTEXT.coverage_dir, self.mutant_name, file_name)
        cmd = [CONTEXT.CONFIG.ENV["GCOVR_EXEC"]]
        if CONTEXT.SUBJECT.subject_configs["cov_compiled_with_clang"] == True:
            cmd.extend(["--gcov-executable", "llvm-cov gcov"])
            cov_cwd=self.repo_dir
        else:
            obj_dir = os.path.join(self.core_dir, CONTEXT.SUBJECT.subject_configs["gcovr_object_root"])
            src_root_dir = os.path.join(self.core_dir, CONTEXT.SUBJECT.subject_configs["gcovr_source_root"])
            if float(CONTEXT.CONFIG.ENV["GCOVR_VERSION"]) < 7.2:
                cmd.extend([
                    "--object-directory", obj_dir,
                    "--root", src_root_dir,
                ])
            else:
                cmd.extend([
                    "--gcov-object-directory", obj_dir,
                    "--root", src_root_dir,
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

    def check_buggy_line_covered(self, CONTEXT: WorkerContext, tc_script_name, raw_cov_file):
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
        elif not "zlib_ng" in self.subject \
            and CONTEXT.SUBJECT.subject_configs["cov_compiled_with_clang"] == False \
            and not "NSFW_c_" in self.subject \
            and not "NSFW_cpp_" in self.subject:
            target_file = self.target_file
        elif "NSFW_c_" in self.subject:
            # cut until src
            target_file = self.target_file.split("src/")[1]
        elif "NSFW_cpp_" in self.subject:
            target_file = self.target_file.split("NSCore/")[1]
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
                        LOGGER.debug(f"{tc_script_name} on {filename} filename and line {cur_lineno} has count: {cur_count}")
                        if line["count"] > 0:
                            return 0
                        else:
                            return 1
                return 1
        return 1
    
    def make_key(self, target_code_file, buggy_lineno, for_buggy_line_key=False):
        # This was include because in case of libxml2
        # gcovr makes target files as <target-file>.c
        # instead of libxml2/<target-file>.c 2024-12-18
        '''
        model_file = ""
        for key, value in self.line2function_dict.items():
            tmp_filename = target_code_file.split("/")[-1]
            if key.endswith(tmp_filename):
                model_file = key
                break
        if model_file == "":
            model_file = target_code_file
        '''

        if "libxml2" in self.subject:
            model_file = target_code_file.split("/")[-1]
        else:
            model_file = target_code_file

        if len(model_file.split("/")) == 1:
            filename = target_code_file.split("/")[-1]
        elif for_buggy_line_key and "zlib_ng" in self.subject:
            filename = "/".join(target_code_file.split("/")[1:])
        elif for_buggy_line_key and ("NSFW_c_" in self.subject):
            filename = target_code_file.split("src/")[1]
        elif for_buggy_line_key and ("NSFW_cpp_" in self.subject):
            filename = target_code_file.split("NSCore/")[1]
        elif not for_buggy_line_key and "vim" in self.subject:
            filename = f"{self.subject}/"+target_code_file
        else:
            filename = target_code_file

        function = None
        for key, value in self.line2function_data.items():
            if key.endswith(filename):
                for func_info in value:
                    if int(func_info[1]) <= int(buggy_lineno) <= int(func_info[2]):
                        function = f"{filename}#{func_info[0]}#{buggy_lineno}"
                        return function
        function = f"{filename}#FUNCTIONNOTFOUND#{buggy_lineno}"
        return function

    def set_target_preprocessed_files(self, CONTEXT: WorkerContext):
        self.target_preprocessed_files = CONTEXT.SUBJECT.subject_configs["target_preprocessed_files"]

    def extract_line2function_mapping(self, CONTEXT: WorkerContext) -> bool:
        # 1. Apply patch
        res = self.apply_patch(revert=False)
        if not res:
            LOGGER.error(f"Failed to apply patch {self.patch_file} to {self.target_file}, skipping mutant")
            return False


        # 2. Build the subject, if build fails, skip the mutant
        res = execute_bash_script(CONTEXT.SUBJECT.build_script, CONTEXT.SUBJECT.build_script_working_directory)
        if res != 0:
            LOGGER.warning(f"Build failed after applying patch {self.patch_file}, skipping mutant")
            self.apply_patch(revert=True)
            return False

        # 3. Extract line2function mapping
        perfile_line2function_data = {}
        for pp_file_str in self.target_preprocessed_files:
            pp_file = os.path.join(self.core_dir, pp_file_str)
            assert os.path.exists(pp_file), f"Preprocessed file {pp_file} does not exist"
            cmd = [CONTEXT.extractor_exec, pp_file]
            process= sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, encoding="utf-8")

            while True:
                line = process.stdout.readline()
                if line == "" and process.poll() != None:
                    break
                line = line.strip()
                if line == "":
                    continue
                    
                # ex) one##htmlReadDoc(const xmlChar * cur, const char * URL, const char * encoding, int options)##6590##6603##HTMLparser.c:6590:1##HTMLparser.c
                data = line.split("##")
                class_name = data[0]
                function_name = data[1]
                start_line = data[2]
                end_line = data[3]
                originated_file = data[4]
                file_data = originated_file.split(":")[0]
                filename = data[5]
                if "vim" in self.subject:
                    file_data = f"{self.subject}/src/"+file_data

                if file_data not in perfile_line2function_data:
                    perfile_line2function_data[file_data] = []
            
                full_function_name = f"{class_name}::{function_name}" if class_name != "None" else function_name
                data = (full_function_name, start_line, end_line)
                if data not in perfile_line2function_data[file_data]:
                    perfile_line2function_data[file_data].append(data)

            LOGGER.debug(f"Extracted line2function data from {os.path.basename(pp_file)}")

        # 4. Apply revert patch
        res = self.apply_patch(revert=True)
        if not res:
            LOGGER.error(f"Failed to revert patch {self.patch_file} to {self.target_file}, skipping mutant")
            return False
        
        # 5. Save line2function mapping
        line2function_file = os.path.join(CONTEXT.line2function_dir, f"{self.mutant_name}_line2function.json")
        with open(line2function_file, 'w') as f:
            json.dump(perfile_line2function_data, f, ensure_ascii=False)
        LOGGER.debug(f"Saved line2function mapping to {line2function_file}")
        
        return True

    def set_line2function_info(self, CONTEXT: WorkerContext):
        line2function_file = os.path.join(CONTEXT.line2function_dir, f"{self.mutant_name}_line2function.json")
        assert os.path.exists(line2function_file), f"Line2Function file {line2function_file} does not exist"
        with open(line2function_file, 'r') as f:
            self.line2function_data = json.load(f)
        LOGGER.debug(f"Loaded line2function mapping from {line2function_file}")
    
    def measure_coverage_for_candidate_test_cases(self, CONTEXT: WorkerContext):
        # 1. Apply patch
        res = self.apply_patch(revert=False)
        if not res:
            LOGGER.error(f"Failed to apply patch {self.patch_file} to {self.target_file}, skipping mutant")
            return False
        
        # 2. Build the subject, if build fails, skip the mutant
        res = execute_bash_script(CONTEXT.SUBJECT.build_script, CONTEXT.SUBJECT.build_script_working_directory)
        if res != 0:
            LOGGER.warning(f"Build failed after applying patch {self.patch_file}, skipping mutant")
            self.apply_patch(revert=True)
            return False
        
        for test_type in ["fail", "pass", "cctc"]:
            for tc_idx, tc_name in self.tc_info[test_type]:
                # 2.1 remove all gcda files
                self.remove_all_gcda()

                # 2.2 run the test case
                res = self.run_test_with_testScript(os.path.join(CONTEXT.testcases_dir, tc_name))
                
                # 2.3 remove untargeted files for gcovr
                self.remove_untargeted_files_for_gcovr(CONTEXT)

                # 2-4. Collect coverage
                raw_cov_file = self.generate_coverage_json(CONTEXT, tc_name)

                # 2-5 Identify cctcs from pjassings tests
                if test_type == "pass":
                    buggy_line_covered = self.check_buggy_line_covered(CONTEXT, tc_name, raw_cov_file)
                    if buggy_line_covered == 0:
                        self.tc_info["cctc"].append((tc_idx, tc_name))
                        LOGGER.debug(f"Candidate correct test case (cctc) found: {tc_name} covers buggy line {self.buggy_lineno}")
                elif test_type == "fail":
                    buggy_line_covered = self.check_buggy_line_covered(CONTEXT, tc_name, raw_cov_file)
                    if buggy_line_covered != 0:
                        LOGGER.error(f"Failing test case {tc_name} does not cover buggy line {self.buggy_lineno}")
                        self.apply_patch(revert=True)
                        raise ValueError(f"Failing test case {tc_name} does not cover buggy line {self.buggy_lineno}")

        if CONTEXT.SUBJECT.subject_configs["test_initialization"]["status"] == True:
            self._save_initialization_tc_cov(CONTEXT)     
            
        # 3. Apply revert patch
        self.apply_patch(revert=True)

        return True
    
    def _save_initialization_tc_cov(self, CONTEXT: WorkerContext):
        # 2.1 remove all gcda files
        self.remove_all_gcda()
        
        # 2.2 execute
        exec_wd = os.path.join(self.core_dir, CONTEXT.SUBJECT.subject_configs["test_initialization"]["execution_path"])
        cmd = CONTEXT.SUBJECT.subject_configs["test_initialization"]["init_cmd"]
        res = sp.run(
            cmd,
            shell=True, cwd=exec_wd, # 2024-08-12 SPECIFICALLY CHANGE THIS MANUALLY
            stderr=sp.PIPE, stdout=sp.PIPE,
            env=os.environ
        )

        # 2.3 remove untargeted files for gcovr
        self.remove_untargeted_files_for_gcovr(CONTEXT)

        # 2-4. Collect coverage
        raw_cov_file = self.generate_coverage_json(CONTEXT, "initialization.00")

    def update_cctcs_in_db(self, DB: CRUD):
        if len(self.tc_info["cctc"]) == 0:
            LOGGER.debug(f"No cctcs found for mutant {self.mutant_name}, not updating DB")
            return
        
        for tc_idx, tc_name in self.tc_info["cctc"]:
            DB.update(
                "cpp_tc_info",
                set_values={
                    "tc_result": "cctc"
                },
                conditions={
                    "bug_idx": self.bug_idx,
                    "tc_idx": tc_idx,
                    "tc_name": tc_name
                }
            )
        
        LOGGER.debug(f"Updated {len(self.tc_info['cctc'])} cctcs for mutant {self.mutant_name} in DB")
        return

    def get_lineKey2lineIdx_from_all_coverage_files(self, CONTEXT: WorkerContext):
        all_line_keys = set()
        
        # Collect all unique line keys from all test case coverage files
        for test_type in ["fail", "pass", "cctc"]:
            for tc_idx, tc_name in self.tc_info[test_type]:
                raw_cov_file = os.path.join(CONTEXT.coverage_dir, self.mutant_name, f"{tc_name.split('.')[0]}.raw.json")
                if os.path.exists(raw_cov_file):
                    with open(raw_cov_file, 'r') as f:
                        cov_data = json.load(f)
                    
                    for file in cov_data["files"]:
                        filename = file["file"]
                        for lineData in file["lines"]:
                            line_number = lineData["line_number"]
                            key = self.make_key(filename, line_number)
                            all_line_keys.add(key)
        
        # Create the mappings
        lineKey2lineIdx = {}
        lineIdx2lineKey = {}
        for idx, key in enumerate(sorted(all_line_keys)):
            lineKey2lineIdx[key] = idx
            lineIdx2lineKey[idx] = key
            
        self.lineKey2lineIdx = lineKey2lineIdx
        self.lineIdx2lineKey = lineIdx2lineKey
        LOGGER.debug(f"Created lineKey2lineIdx mapping with {len(all_line_keys)} unique lines")

    def get_lineCovBitVal_from_tc_list(self, CONTEXT: WorkerContext, tc_list: list):
        tcsIdx2lineCovBitVal = {}
        for tc_idx, tc_name in tc_list:
            lineCovBitSeq = ['0'] * len(self.lineKey2lineIdx)
            raw_cov_file = os.path.join(CONTEXT.coverage_dir, self.mutant_name, f"{tc_name.split('.')[0]}.raw.json")
            with open(raw_cov_file, 'r') as f:
                cov_data = json.load(f)
            
            for file in cov_data["files"]:
                filename = file["file"]
                for lineIdx, lineData in enumerate(file["lines"]):
                    line_number = lineData["line_number"]
                    count = lineData["count"]
                    key = self.make_key(filename, line_number)
                    idx = self.lineKey2lineIdx[key]

                    if int(count) > 0:
                        lineCovBitSeq[idx] = '1'
            tcsIdx2lineCovBitVal[tc_idx] = int("".join(lineCovBitSeq), 2)
        return tcsIdx2lineCovBitVal
    
    def _get_lineCovBitVal_for_initialization_cmd(self, CONTEXT: WorkerContext):
        lineCovBitSeq = ['0'] * len(self.lineKey2lineIdx)
        raw_cov_file = os.path.join(CONTEXT.coverage_dir, self.mutant_name, "initialization.raw.json")
        with open(raw_cov_file, 'r') as f:
            cov_data = json.load(f)
        
        for file in cov_data["files"]:
            filename = file["file"]
            for lineIdx, lineData in enumerate(file["lines"]):
                line_number = lineData["line_number"]
                count = lineData["count"]
                key = self.make_key(filename, line_number)
                idx = self.lineKey2lineIdx[key]

                if int(count) > 0:
                    lineCovBitSeq[idx] = '1'
        return int("".join(lineCovBitSeq), 2)
    
    def save_candidate_lines_to_db(self, DB: CRUD, candidate_lineKeys2newlineIdx: dict):
        buggy_file, buggy_function, buggy_lineno = self.buggy_line_key.split("#")
        for lineKey, newIdx in candidate_lineKeys2newlineIdx.items():
            filename, function_name, lineno = lineKey.split("#")

            is_buggy_line = False
            if buggy_file == filename \
                and buggy_function == function_name \
                and buggy_lineno == lineno:
                is_buggy_line = True
            
            values = [
                self.bug_idx,
                filename, function_name, int(lineno),
                newIdx, is_buggy_line
            ]
            
            DB.insert(
                "cpp_line_info",
                "bug_idx, file, function, lineno, line_idx, is_buggy_line",
                values
            )
    
    def update_tc_result_to_irrelevant(self, DB: CRUD, notRelevantTCs: list):       
        for tc_result_type in ["fail", "pass", "cctc", "crashed"]:
            for tc_idx, tc_name in self.tc_info[tc_result_type]:
                relevant_status = True
                if tc_idx in notRelevantTCs or tc_result_type == "crashed" or tc_result_type == "cctc":
                    relevant_status = False

                DB.update(
                    "cpp_tc_info",
                    set_values={"relevant_tcs": relevant_status},
                    conditions={
                        "bug_idx": self.bug_idx,
                        "tc_idx": tc_idx,
                        "tc_name": tc_name
                    }
                )
    
    def save_lineCovBit_to_db(self, DB: CRUD, tcs2lineCovBitVal: dict, tc_type: str, suffix: str, numLines: int):
        bit_sequence_length_col = f"{suffix}bit_sequence_length"
        line_coverage_bit_sequence_col = f"{suffix}line_coverage_bit_sequence"

        updated_count = 0
        for tc_idx, lineCovBitVal in tcs2lineCovBitVal.items():
            lineCovBitValStr = format(lineCovBitVal, f'0{numLines}b')
            values = {
                bit_sequence_length_col: numLines,
                line_coverage_bit_sequence_col: lineCovBitValStr
            }
            DB.update(
                "cpp_tc_info",
                set_values=values,
                conditions={
                    "bug_idx": self.bug_idx,
                    "tc_idx": tc_idx,
                    "tc_result": tc_type
                }
            )
            updated_count += 1
        LOGGER.debug(f"Updated {updated_count} {tc_type} test cases in DB with {suffix}lineCovBitVal")

    def postprocess_coverage_info(self, CONTEXT: WorkerContext, DB: CRUD = None):
        # 1. set buggy_line_key
        self.buggy_line_key = self.make_key(self.target_code_file, self.buggy_lineno, for_buggy_line_key=True)
        buggy_file, buggy_function, buggy_lineno = self.buggy_line_key.split("#")
        DB.update("cpp_bug_info",
            set_values={
                "buggy_file": buggy_file,
                "buggy_function": buggy_function,
                "buggy_lineno": int(buggy_lineno)
            },
            conditions={
                "bug_idx": self.bug_idx,
                "subject": self.subject,
                "experiment_label": self.experiment_label,
                "version": self.mutant_name
            }
        )
        LOGGER.debug(f"buggy_line_key: {self.buggy_line_key}")

        # 2. set lineKey2lineIdx using all test case coverage files
        first_raw_cov_file = os.path.join(CONTEXT.coverage_dir, self.mutant_name, f"{self.tc_info['fail'][0][1].split('.')[0]}.raw.json")
        LOGGER.debug(f"Creating lineKey2lineIdx from: {first_raw_cov_file}")
        
        self.get_lineKey2lineIdx_from_all_coverage_files(CONTEXT)
        LOGGER.debug(f"Total lines in lineKey2lineIdx: {len(self.lineKey2lineIdx)}")

        # 3. Get coverage info for each test case list
        numTotalLines = len(self.lineKey2lineIdx)

        failTcs2lineCovBitVal = self.get_lineCovBitVal_from_tc_list(CONTEXT, self.tc_info["fail"])
        failLinesBitVal = merge_lineCovBitVal(failTcs2lineCovBitVal)
        failLinesBitValStr = format(failLinesBitVal, f'0{len(self.lineKey2lineIdx)}b')
        numLinesExecutedByFailingTCs = failLinesBitValStr.count("1")

        passTcs2lineCovBitVal = self.get_lineCovBitVal_from_tc_list(CONTEXT, self.tc_info["pass"])
        passLinesBitVal = merge_lineCovBitVal(passTcs2lineCovBitVal)
        passLinesBitValStr = format(passLinesBitVal, f'0{len(self.lineKey2lineIdx)}b')
        numLinesExecutedByPassingTCs = passLinesBitValStr.count("1")

        cctcTcs2lineCovBitVal = self.get_lineCovBitVal_from_tc_list(CONTEXT, self.tc_info["cctc"])
        cctcLinesBitVal = merge_lineCovBitVal(cctcTcs2lineCovBitVal)
        cctcLinesBitValStr = format(cctcLinesBitVal, f'0{len(self.lineKey2lineIdx)}b')
        numLinesExecutedByCCTCs = cctcLinesBitValStr.count("1")

        totalNumLinesExecutedStr = format((failLinesBitVal | passLinesBitVal | cctcLinesBitVal), f'0{len(self.lineKey2lineIdx)}b')
        numTotalLinesExecuted = totalNumLinesExecutedStr.count("1")

        # 4. Get candidate lines which are lines executed by failing test cases
        candidate_lineKeys2newlineIdx = {}
        newIdx = -1
        for bitCharIdx, bitChar in enumerate(failLinesBitValStr):
            if bitChar == '1':
                newIdx += 1
                lineKey = self.lineIdx2lineKey[bitCharIdx]
                candidate_lineKeys2newlineIdx[lineKey] = newIdx
                if lineKey == self.buggy_line_key:
                    LOGGER.debug(f"FOUND buggy line in candidates: {lineKey}")
        
        self.save_candidate_lines_to_db(DB, candidate_lineKeys2newlineIdx)
        
        # 5. Identify not-relevant test cases among passing and cctc test cases
        # not-relevant test cases are test cases that do not cover any candidate lines
        notRelevantTCs = []
        passIrrelevant = identify_not_relevant_tcs(passTcs2lineCovBitVal, failLinesBitVal)
        cctcsIrrelevant = identify_not_relevant_tcs(cctcTcs2lineCovBitVal, failLinesBitVal)
        LOGGER.debug(f"Identified {len(passIrrelevant)} irrelevant passing test cases")
        LOGGER.debug(f"Identified {len(cctcsIrrelevant)} irrelevant cctc test cases")
        notRelevantTCs.extend(passIrrelevant)
        notRelevantTCs.extend(cctcsIrrelevant)
        LOGGER.debug(f"Total {len(notRelevantTCs)} irrelevant test cases")
        
        self.update_tc_result_to_irrelevant(DB, notRelevantTCs)

        # 6. Reform covBitVal to only include candidate lines
        reformedFailTcs2lineCovBitVal = reform_covBitVal_to_candidate_lines(failTcs2lineCovBitVal, candidate_lineKeys2newlineIdx, numTotalLines, self.lineIdx2lineKey)
        reformedPassTcs2lineCovBitVal = reform_covBitVal_to_candidate_lines(passTcs2lineCovBitVal, candidate_lineKeys2newlineIdx, numTotalLines, self.lineIdx2lineKey)
        reformedCctcTcs2lineCovBitVal = reform_covBitVal_to_candidate_lines(cctcTcs2lineCovBitVal, candidate_lineKeys2newlineIdx, numTotalLines, self.lineIdx2lineKey)

        if CONTEXT.SUBJECT.subject_configs["test_initialization"]["status"] == True:
            initializationCovBitVal = self._get_lineCovBitVal_for_initialization_cmd(CONTEXT)
            # LOGGER.debug(f"achieved initializationCovBitVal: {initializationCovBitVal}")
            reformedInitializationCovBitVal = reform_covBitVal_to_candidate_lines(
                {"initialization_cmd": initializationCovBitVal},
                candidate_lineKeys2newlineIdx, 
                numTotalLines, self.lineIdx2lineKey
            )
            initLineCovBitValStr = format(initializationCovBitVal, f'0{numTotalLines}b')
            reformedInitLineCovBitValStr = format(reformedInitializationCovBitVal["initialization_cmd"], f'0{len(candidate_lineKeys2newlineIdx)}b')
            cols = [
                "bug_idx", "tc_idx", "tc_name",
                "tc_result", "tc_ret_code", "execution_time_ms",
                "full_bit_sequence_length", "full_line_coverage_bit_sequence",
                "bit_sequence_length", "line_coverage_bit_sequence",
                "relevant_tcs"
            ]
            col_str = ", ".join(cols)
            values = [
                self.bug_idx, -1, "initialization",
                "initialization", 0, 0,
                numTotalLines, initLineCovBitValStr,
                len(candidate_lineKeys2newlineIdx), reformedInitLineCovBitValStr,
                False
            ]
            DB.insert("cpp_tc_info", col_str, values)

        self.save_lineCovBit_to_db(DB, failTcs2lineCovBitVal, "fail", "full_", numTotalLines)
        self.save_lineCovBit_to_db(DB, passTcs2lineCovBitVal, "pass", "full_", numTotalLines)
        self.save_lineCovBit_to_db(DB, cctcTcs2lineCovBitVal, "cctc", "full_", numTotalLines)
        self.save_lineCovBit_to_db(DB, reformedFailTcs2lineCovBitVal, "fail", "", len(candidate_lineKeys2newlineIdx))
        self.save_lineCovBit_to_db(DB, reformedPassTcs2lineCovBitVal, "pass", "", len(candidate_lineKeys2newlineIdx))
        self.save_lineCovBit_to_db(DB, reformedCctcTcs2lineCovBitVal, "cctc", "", len(candidate_lineKeys2newlineIdx))

        # 7. Prepare coverage summary
        coverage_summary = {
            "num_failing_tcs": len(self.tc_info["fail"]),
            "num_passing_tcs": len(self.tc_info["pass"]),
            "num_ccts": len(self.tc_info["cctc"]),
            "num_total_tcs": len(self.tc_info["fail"]) + len(self.tc_info["pass"]) + len(self.tc_info["cctc"]),
            "num_lines_executed_by_failing_tcs": numLinesExecutedByFailingTCs,
            "num_lines_executed_by_passing_tcs": numLinesExecutedByPassingTCs,
            'num_lines_executed_by_ccts': numLinesExecutedByCCTCs,
            "num_total_lines_executed": numTotalLinesExecuted,
            "num_total_lines": numTotalLines,
        }

        LOGGER.debug(json.dumps(coverage_summary, indent=4))

        DB.update(
            "cpp_bug_info",
            set_values=coverage_summary,
            conditions={
                "bug_idx": self.bug_idx,
                "subject": self.subject,
                "experiment_label": self.experiment_label,
                "version": self.mutant_name
            }
        )

    def extract_execution_command(self, tc_script: str) -> str:
        # TODO:
        # PROBABLITY WILL NEED TO MODIFY FOR THIS FOR DIFFERENT SUBJECT
        # BECAUSE DIFFERENT SUBJECTS HAVE DIFFERENT TEST SCRIPT FORMATS
        return extract_execution_cmd_from_test_script_file(tc_script)

    def extract_stack_trace_for_failing_tests(self, CONTEXT: WorkerContext, DB: CRUD):
        LOGGER.debug(f"starting stack trace extraction")
        test_execution_point = os.path.join(self.core_dir, CONTEXT.SUBJECT.subject_configs["testcase_execution_point"])
        source_code_filename = self.target_code_file.split("/")[-1]
        line_number = self.buggy_lineno
        for tc_idx, tc_name in self.tc_info["fail"]:
            tc_script_path = os.path.join(CONTEXT.testcases_dir, tc_name)

            # 1. make execution command
            execution_cmd = self.extract_execution_command(tc_script_path)
            
            # 2. make gdb script
            if "NSFW_cpp_" in self.subject:
                gdb_script_txt = make_gdb_script_txt_cpp(test_execution_point, source_code_filename, line_number)
            else:
                gdb_script_txt = make_gdb_script_txt(test_execution_point, source_code_filename, line_number)

            # 3. run gdb
            gdb_cmd = f"gdb -x gdb_script.txt -batch --args {execution_cmd}"
            gdb_result = sp.run(
                    gdb_cmd,
                    shell=True,
                    stderr=sp.PIPE,
                    stdout=sp.PIPE,
                    encoding="utf-8",
                    cwd=test_execution_point
                )
            
            bt_list = parse_gdb_output_for_stack_trace(gdb_result.stdout.split("\n"))
            stack_trace = "".join(bt_list)

            # 4. save stack trace to DB
            if stack_trace != "":
                LOGGER.debug(stack_trace)
                DB.update(
                    "cpp_tc_info",
                    set_values={"stacktrace": stack_trace},
                    conditions={
                        "bug_idx": self.bug_idx,
                        "tc_idx": tc_idx,
                        "tc_name": tc_name
                    }
                )


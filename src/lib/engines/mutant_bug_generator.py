import logging
import os
import concurrent.futures
import queue
import threading
from pathlib import Path

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

# Not using operators when collecting buggy mutants
not_using_operators_in_buggy_mutant_collection = [
    "DirVarAriNeg", "DirVarBitNeg", "DirVarLogNeg", "DirVarIncDec",
    "DirVarRepReq", "DirVarRepCon", "DirVarRepPar", "DirVarRepGlo", 
    "DirVarRepExt", "DirVarRepLoc", "IndVarAriNeg", "IndVarBitNeg", 
    "IndVarLogNeg", "IndVarIncDec", "IndVarRepReq", "IndVarRepCon", 
    "IndVarRepPar", "IndVarRepGlo", "IndVarRepExt", "IndVarRepLoc",
    "SSDL", "CovAllNod", "CovAllEdg", "STRP", "STRI", "VDTR",
    "RetStaDel", "FunCalDel", "SMVB",
    "SMTC" # This makes music to see buggy line as line at "{"
]

without_some_mut_op = [
    "dxt.cpp", "arabic.c", "blowfish.c", "cmdexpand.c", "diff.c",
    "digraph.c", "window.c", "version.c", "term.c", "sha256.c",
    "regexp_bt.c", "misc2.c", "mbyte.c", "map.c", "unicode.c",
    "pen.c", "mouse.c", "keyboard.c", "encoding.c", "json.c",
    "highlight.c", "help.c",
]

class MutantBugGenerator(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutantBugGenerator initialized")
    
    def run(self):
        """Execute the mutant bug generation process"""
        LOGGER.info("Running Mutant Bug Generator")

        # Initialize cpp_bug_info table
        self._initialize_required_tables()

        # Make required directories 'generated_mutants' and per-file directories
        target_file_info_list = self.make_required_directories()

        # Configure with no coverage option & build
        execute_bash_script(self.SUBJECT.configure_no_cov_script, self.dest_repo)
        execute_bash_script(self.SUBJECT.build_script, self.dest_repo)

        # Generate mutants for each target file
        self.generate_mutants_for_target_files(target_file_info_list)
        mutant_lists = self.get_generated_mutants(target_file_info_list)

        # Clean up build artifacts
        execute_bash_script(self.SUBJECT.clean_script, self.dest_repo)

        self.start_testing_for_mutant_bugs(mutant_lists)


    def make_required_directories(self) -> list:
        # Make directory to save generated mutants
        self.generated_mutants_dir = os.path.join(self.out_dir, "generated_mutants")
        self.FILE_MANAGER.make_directory(self.generated_mutants_dir)

        # Make directory for each target file
        target_file_info_list = []
        for target_file in self.SUBJECT.subject_configs["target_files"]:
            target_file_path = os.path.join(self.working_dir, target_file)
            assert os.path.exists(target_file_path), f"Target file does not exist: {target_file_path}"

            target_file_mutant_dir_name = target_file.replace("/", "#")
            target_file_mutant_dir_path = os.path.join(self.generated_mutants_dir, target_file_mutant_dir_name)
            self.FILE_MANAGER.make_directory(target_file_mutant_dir_path)
            target_file_info_list.append((target_file_path, target_file_mutant_dir_path))

        return target_file_info_list
    
    def generate_mutants_for_target_files(self, target_file_info_list: list):
        def _check_if_mutant_generation_needed(target_file_mutant_dir_path: str) -> bool:
            # Check if the mutant directory is empty
            return not os.listdir(target_file_mutant_dir_path)

        def _worker(task_queue, worker_id):
            while True:
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break

                    target_file_path, target_file_mutant_dir_path = task
                    LOGGER.info(f"Worker {worker_id}: Generating mutants for {target_file_path}")

                    try:
                        if not _check_if_mutant_generation_needed(target_file_mutant_dir_path):
                            LOGGER.info(f"Worker {worker_id}: Mutants already exist for {target_file_path}, skipping generation")
                        else:
                            _generate_mutants_for_single_file(target_file_path, target_file_mutant_dir_path)
                    except Exception as e:
                        LOGGER.error(f"Worker {worker_id}: Error generating mutants for {target_file_path}: {e}")
                    finally:
                        task_queue.task_done()
                except queue.Empty:
                    break
                except Exception as e:
                    LOGGER.error(f"Worker {worker_id}: Encountered an error: {e}")
            LOGGER.info(f"Worker {worker_id}: Exiting generating mutants")

        def _generate_mutants_for_single_file(target_file_path: str, target_file_mutant_dir_path: str):
            unused_ops = ",".join(not_using_operators_in_buggy_mutant_collection)
            if os.path.basename(target_file_mutant_dir_path) in without_some_mut_op:
                unused_ops += "," + ",".join(["CGCR", "CLCR", "CGSR", "CLSR"])
            
            cmd = [
                self.musicup_exec,
                str(target_file_path),
                "-o", str(target_file_mutant_dir_path),
                "-ll", "1",
                "-l", "20",
                "-d", unused_ops,
                "-p", str(self.SUBJECT.compile_commands_json_path)
            ]
            execute_command_as_list(cmd)
            LOGGER.info(f"Mutants generated for {target_file_path} in {target_file_mutant_dir_path}")

        task_queue = queue.Queue()
        for target_file_path, target_file_mutant_dir_path in target_file_info_list:
            task_queue.put((target_file_path, target_file_mutant_dir_path))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(_worker, task_queue, worker_id)
                for worker_id in range(5)
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    LOGGER.error(f"Worker encountered an error: {e}")
    
    def get_generated_mutants(self, target_file_info_list: list) -> dict:
        mutant_list = []
        
        extension = "*.c" if self.CONFIG.ENV["LANGUAGE"] == "c" else "*.cpp"

        for target_file_path, target_file_mutant_dir_path in target_file_info_list:
            LOGGER.debug(f"Collecting mutants from {target_file_mutant_dir_path}")
            target_file = target_file_mutant_dir_path.replace("#", "/")          
            target_mutants = list(Path(target_file_mutant_dir_path).glob(extension))
            for mutant in target_mutants:
                mutant_list.append((target_file, mutant))
            LOGGER.info(f"Collected {len(target_mutants)} mutants for {target_file}")
        return mutant_list

    def start_testing_for_mutant_bugs(self, mutant_lists: list):
        self.EXECUTOR.test_for_mutant_bugs(self.CONTEXT, mutant_lists)

    def cleanup(self):
        """Clean up resources used by the mutant bug generator"""
        LOGGER.info("Cleaning up MutantBugGenerator resources")
        super().cleanup()

    # Initialize required tables in the database
    def _initialize_required_tables(self):
        def _init_cpp_bug_info_table():
            # Create table if not exists: cpp_bug_info
            if not self.DB.table_exists("cpp_bug_info"):
                columns = [
                    "bug_idx SERIAL PRIMARY KEY", # -- Surrogate key
                    "subject TEXT",
                    "experiment_label TEXT",
                    "version TEXT",
                    "type TEXT",
                    "target_code_file TEXT",
                    "buggy_code_file TEXT",
                    "UNIQUE (subject, experiment_label, version)", # -- Ensure uniqueness
                    
                    "mut_op TEXT",
                    "pre_start_line INT",
                    "pre_start_col INT",
                    "pre_end_line INT",
                    "pre_end_col INT",
                    "pre_mut TEXT",
                    "post_start_line INT",
                    "post_start_col INT",
                    "post_end_line INT",
                    "post_end_col INT",
                    "post_mut TEXT"
                ]
                col_str = ", ".join(columns)
                self.DB.create_table("cpp_bug_info", col_str)

        def _init_cpp_tc_info_table():
            # Create table if not exists: tc_info
            if not self.DB.table_exists("cpp_tc_info"):
                columns = [
                    "bug_idx INT NOT NULL", # -- Foreign key to bug_info(bug_idx)
                    
                    "tc_idx INT",
                    "tc_name TEXT",
                    "tc_result TEXT",
                    "tc_ret_code INT",
                    "executione_time_ms DOUBLE PRECISION",

                    "bit_sequence_length INT",
                    "line_coverage_bit_sequence TEXT",

                    "exception_type TEXT",
                    "exception_msg TEXT",
                    "stacktrace TEXT",

                    "FOREIGN KEY (bug_idx) REFERENCES bug_info(bug_idx) ON DELETE CASCADE ON UPDATE CASCADE" # -- Automatically delete tc_info rows when bug_info is deleted, Update changes in bug_info to tc_info
                ]
                col_str = ", ".join(columns)
                self.DB.create_table("cpp_tc_info", col_str)
                # Create a composite index on (subject, experiment_name, version)
                self.DB.create_index(
                    "tc_info",
                    "idx_tc_info_bug_idx",
                    "bug_idx"
                )
        
        _init_cpp_bug_info_table()
        _init_cpp_tc_info_table()
        LOGGER.debug("Required database tables initialized")
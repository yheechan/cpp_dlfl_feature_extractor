import logging
import os
import concurrent.futures
import queue
from pathlib import Path
import csv

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
        target_file_info_list = self._make_required_directories()

        # Configure with no coverage option & build
        execute_bash_script(self.SUBJECT.configure_no_cov_script, self.dest_repo)
        execute_bash_script(self.SUBJECT.build_script, self.dest_repo)

        # Generate mutants for each target file
        self._generate_mutants_for_target_files(target_file_info_list)
        mutant_list = self._get_generated_mutants(target_file_info_list)

        # Clean up build artifacts
        execute_bash_script(self.SUBJECT.clean_script, self.dest_repo)

        self._start_testing_for_mutant_bugs(mutant_list)

        # Write mutation information to the database
        self._write_mutation_info_to_db(mutant_list)


    def _make_required_directories(self) -> list:
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
            target_file_info_list.append((target_file, target_file_path, target_file_mutant_dir_path))

        return target_file_info_list

    def _generate_mutants_for_target_files(self, target_file_info_list: list):
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
        for target_file, target_file_path, target_file_mutant_dir_path in target_file_info_list:
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
    
    def _get_generated_mutants(self, target_file_info_list: list) -> dict:
        mutant_list = []
        
        extension = "*.c" if self.CONFIG.ENV["LANGUAGE"] == "c" else "*.cpp"

        for target_file, target_file_path, target_file_mutant_dir_path in target_file_info_list:
            LOGGER.debug(f"Collecting mutants from {target_file_mutant_dir_path}")
            target_mutants = list(Path(target_file_mutant_dir_path).glob(extension))
            for mutant in target_mutants:
                mutant_list.append((target_file, mutant, target_file_mutant_dir_path))
            LOGGER.info(f"Collected {len(target_mutants)} mutants for {target_file}")
        return mutant_list

    def _start_testing_for_mutant_bugs(self, mutant_list: list):
        self.EXECUTOR.test_for_mutant_bugs(self.CONTEXT, mutant_list)

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
                    "mutant_type TEXT",
                    "target_code_file TEXT",
                    "buggy_code_file TEXT",
                    "UNIQUE (subject, experiment_label, version)", # -- Ensure uniqueness

                    "initial BOOLEAN DEFAULT NULL",
                    "usable BOOLEAN DEFAULT NULL",
                    "prerequisites BOOLEAN DEFAULT NULL",
                    "sbfl BOOLEAN DEFAULT NULL",
                    "mlfl BOOLEAN DEFAULT NULL",
                    "selected_for_mbfl BOOLEAN DEFAULT NULL",
                    "mbfl_cpu_time FLOAT",

                    "buggy_file TEXT DEFAULT NULL",
                    "buggy_function TEXT DEFAULT NULL",
                    "buggy_lineno INT DEFAULT NULL",
                    "buggy_line_idx INT DEFAULT NULL",

                    "num_failing_tcs INT",
                    "num_passing_tcs INT",
                    "num_ccts INT",
                    "num_total_tcs INT",
                    "num_lines_executed_by_failing_tcs INT",
                    "num_lines_executed_by_passing_tcs INT",
                    "num_lines_executed_by_ccts INT",
                    "num_total_lines_executed INT",
                    "num_total_lines INT",

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
                    "post_mut TEXT",
                ]
                col_str = ", ".join(columns)
                self.DB.create_table("cpp_bug_info", col_str)

        def _init_cpp_tc_info_table():
            # Create table if not exists: tc_info
            if not self.DB.table_exists("cpp_tc_info"):
                columns = [
                    "bug_idx INT NOT NULL", # -- Foreign key to cpp_bug_info(bug_idx)
                    
                    "tc_idx INT",
                    "tc_name TEXT",
                    "tc_result TEXT",
                    "tc_ret_code INT",
                    "execution_time_ms DOUBLE PRECISION",

                    "bit_sequence_length INT",
                    "line_coverage_bit_sequence TEXT",
                    "full_bit_sequence_length INT",
                    "full_line_coverage_bit_sequence TEXT",

                    "exception_type TEXT",
                    "exception_msg TEXT",
                    "stacktrace TEXT",

                    "relevant_tcs BOOLEAN DEFAULT NULL",

                    "FOREIGN KEY (bug_idx) REFERENCES cpp_bug_info(bug_idx) ON DELETE CASCADE ON UPDATE CASCADE" # -- Automatically delete tc_info rows when bug_info is deleted, Update changes in bug_info to tc_info
                ]
                col_str = ", ".join(columns)
                self.DB.create_table("cpp_tc_info", col_str)
                # Create a composite index on (subject, experiment_name, version)
                self.DB.create_index(
                    "cpp_tc_info",
                    "idx_cpp_tc_info_bug_idx",
                    "bug_idx"
                )
        
        _init_cpp_bug_info_table()
        _init_cpp_tc_info_table()
        LOGGER.debug("Required database tables initialized")

    def _write_mutation_info_to_db(self, mutant_list: list):
        mutation_info_record = self.get_mutation_info_record()

        for target_file, mutant, target_file_mutant_dir_path in mutant_list:
            assert target_file in mutation_info_record, f"No mutation info found for target file: {target_file}"
            assert mutant.name in mutation_info_record[target_file], f"No mutation info found for mutant: {mutant.name}"

            mutant_data = mutation_info_record[target_file][mutant.name]
            values = {
                "mut_op": mutant_data["mut_op"],
                "pre_start_line": mutant_data["pre_start_line"],
                "pre_start_col": mutant_data["pre_start_col"],
                "pre_end_line": mutant_data["pre_end_line"],
                "pre_end_col": mutant_data["pre_end_col"],
                "pre_mut": mutant_data["pre_mut"],
                "post_start_line": mutant_data["post_start_line"],
                "post_start_col": mutant_data["post_start_col"],
                "post_end_line": mutant_data["post_end_line"],
                "post_end_col": mutant_data["post_end_col"],
                "post_mut": mutant_data["post_mut"]
            }

            bug_info = self.DB.read(
                "cpp_bug_info",
                columns="bug_idx, version, target_code_file",
                conditions={
                    "subject": self.CONFIG.ARGS.subject,
                    "experiment_label": self.CONFIG.ARGS.experiment_label,
                    "version": mutant.name,
                    "target_code_file": target_file
                }
            )
            bug_idx = bug_info[0][0] if len(bug_info) > 0 else None
            assert bug_idx is not None, f"No bug info found in DB for mutant {mutant.name}"

            conditions = {
                "subject": self.CONFIG.ARGS.subject,
                "experiment_label": self.CONFIG.ARGS.experiment_label,
                "bug_idx": bug_idx,
                "version": mutant.name,
                "target_code_file": target_file,
            }

            self.DB.update(
                "cpp_bug_info",
                set_values=values,
                conditions=conditions
            )
            LOGGER.debug(f"Updated mutation info in DB for mutant {mutant.name}")

    def get_mutation_info_record(self):
        mutation_info_record = {}
        
        for target_file in self.SUBJECT.subject_configs["target_files"]:
            target_file_mutant_dir_name = target_file.replace("/", "#")
            target_file_mutant_dir_path = os.path.join(self.generated_mutants_dir, target_file_mutant_dir_name)
            target_file_source_filename= ".".join(target_file.split("/")[-1].split(".")[:-1])
            mut_db_file = os.path.join(target_file_mutant_dir_path, f"{target_file_source_filename}_mut_db.csv")
            
            if not os.path.exists(mut_db_file):
                LOGGER.error(f"Mutation database file not found: {mut_db_file}")
                raise FileNotFoundError(f"Mutation database file not found: {mut_db_file}")

            if target_file not in mutation_info_record:
                mutation_info_record[target_file] = {}
            
            with open(mut_db_file, "r") as fp:
                # read with csv
                csv_reader = csv.reader(fp, escapechar='\\', quotechar='"', delimiter=',')
                next(csv_reader)
                next(csv_reader)
                for row in csv_reader:
                    mut_name = row[0]
                    op = row[1]
                    pre_start_line = row[2]
                    pre_start_col = row[3]
                    pre_end_line = row[4]
                    pre_end_col = row[5]
                    pre_mut = row[6]
                    post_start_line = row[7]
                    post_start_col = row[8]
                    post_end_line = row[9]
                    post_end_col = row[10]
                    post_mut = row[11]

                    mutation_info_record[target_file][mut_name] = {
                        "mut_op": op,
                        "pre_start_line": pre_start_line,
                        "pre_start_col": pre_start_col,
                        "pre_end_line": pre_end_line,
                        "pre_end_col": pre_end_col,
                        "pre_mut": pre_mut,
                        "post_start_line": post_start_line,
                        "post_start_col": post_start_col,
                        "post_end_line": post_end_line,
                        "post_end_col": post_end_col,
                        "post_mut": post_mut
                    }
        return mutation_info_record

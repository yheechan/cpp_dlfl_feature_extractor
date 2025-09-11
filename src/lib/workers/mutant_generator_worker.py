import os
from pathlib import Path
import csv


from lib.workers.worker import Worker
from lib.experiment_configs import ExperimentConfigs
from lib.mutant import Mutant

from utils.command_utils import *


not_using_operators_in_mbfl = [
    "DirVarAriNeg", "DirVarBitNeg", "DirVarLogNeg", "DirVarIncDec",
    "DirVarRepReq", "DirVarRepCon", "DirVarRepPar", "DirVarRepGlo", 
    "DirVarRepExt", "DirVarRepLoc", "IndVarAriNeg", "IndVarBitNeg", 
    "IndVarLogNeg", "IndVarIncDec", "IndVarRepReq", "IndVarRepCon", 
    "IndVarRepPar", "IndVarRepGlo", "IndVarRepExt", "IndVarRepLoc",
    "STRI"
]
UNUSED_OPS=",".join(not_using_operators_in_mbfl)

class MutantGeneratorWorker(Worker):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutantGeneratorWorker initialized")

        self.version_mutant_mutants_dir = os.path.join(self.mutant_mutants_dir, self.CONFIG.ARGS.mutant)
        if not os.path.exists(self.version_mutant_mutants_dir):
            os.makedirs(self.version_mutant_mutants_dir, exist_ok=True)
        LOGGER.debug(f"Version mutant_mutants directory: {self.version_mutant_mutants_dir}")

    def execute(self):
        """Execute the mutant generation process"""
        LOGGER.info("Executing Mutant Generator Worker")

        # 1. Configure subject
        if self.CONFIG.ARGS.needs_configuration:
            LOGGER.info("Configuring subject")
            execute_bash_script(self.SUBJECT.configure_yes_cov_script, self.subject_repo)
        
        # 2. Build subject
        LOGGER.info("Building subject")
        execute_bash_script(self.SUBJECT.build_script, self.subject_repo)

        # 3. Generate mutant mutants
        LOGGER.info("Generating mutant mutants")
        self._generate_mutant_mutants()


    def _generate_mutant_mutants(self):
        LOGGER.debug(f"target_file: {self.CONFIG.ARGS.target_file}, mutant: {self.CONFIG.ARGS.mutant}")
        # set MUTANT
        MUTANT = self.make_mutant()

        # 1. set MUTANT basic info
        MUTANT.set_bug_idx_from_db(self.DB)
        MUTANT.set_line_info_from_db(self.DB)

        # 2. make patch file
        res = MUTANT.apply_patch(revert=False)
        if not res:
            LOGGER.error(f"Failed to apply patch {MUTANT.patch_file} to {MUTANT.target_file}, skipping mutant")
            return
        
        # 3. Clean the build
        res = execute_bash_script(self.SUBJECT.clean_script, self.subject_repo)
        if res != 0:
            LOGGER.error(f"Failed to clean the build, skipping mutant")
            MUTANT.apply_patch(revert=True)
            return

        # 4. Configure with no coverage option
        res = execute_bash_script(self.SUBJECT.configure_no_cov_script, self.subject_repo)
        if res != 0:
            LOGGER.error(f"Failed to configure subject with no coverage option, skipping mutant")
            MUTANT.apply_patch(revert=True)
            return

        # 6. Build the subject, if build fails, skip the mutant
        res = execute_bash_script(self.SUBJECT.build_script, self.subject_repo)
        if res != 0:
            LOGGER.error(f"Build failed after applying patch {MUTANT.patch_file}, skipping mutant")
            MUTANT.apply_patch(revert=True)
            return
        self.SUBJECT.set_environmental_variables(self.core_dir)

        # 7. Organize targetFile2fileInfo dictionary
        targetFile2fileInfo = self._organize_targetFile2fileInfo(MUTANT)
        
        # 8. Generate mutant mutants
        target_file_mutant_dirs = [dir for dir in os.listdir(self.version_mutant_mutants_dir)]
        if len(target_file_mutant_dirs) == 0:
            LOGGER.debug("No target file mutant directories found, skipping mutant generation")
            # 9. make required directories that will hold the mutant mutants
            self._make_required_directories_for_mutant_mutants(MUTANT)

            self._generate_mutants_for_target_files_only_only_selected_lines(targetFile2fileInfo)
        else:
            LOGGER.debug(f"Found target file mutant directories: {target_file_mutant_dirs}")

        # 7. Get generated mutants
        generated_mutants = self._get_generated_mutants(targetFile2fileInfo)
        LOGGER.debug(f"Generated {len(generated_mutants)} mutants for mutant {MUTANT.mutant_file}")

        # 8. Get mutation info record from music csv-DB
        mutation_info_record = self._get_mutation_info_record(targetFile2fileInfo, MUTANT=MUTANT)

        # 9, Insert generated mutants into DB
        self._insert_generated_mutants_into_db(generated_mutants, mutation_info_record, MUTANT)

    def _make_required_directories_for_mutant_mutants(self, MUTANT: Mutant):
        target_files = []
        for lineIdx, lineInfo in MUTANT.lineIdx2lineKey.items():
            target_file = lineInfo["file"]
            if target_file not in target_files:
                target_files.append(target_file)

                target_file_mutant_dir_name = target_file.replace("/", "#")
                target_file_mutant_dir_path = os.path.join(self.version_mutant_mutants_dir, target_file_mutant_dir_name)
                if not os.path.exists(target_file_mutant_dir_path):
                    os.makedirs(target_file_mutant_dir_path, exist_ok=True)
                    LOGGER.debug(f"Created directory for mutant mutants: {target_file_mutant_dir_path}")
                else:
                    LOGGER.debug(f"Directory for mutant mutants already exists: {target_file_mutant_dir_path}")

    def _organize_targetFile2fileInfo(self, MUTANT: Mutant):
        targetFiles2fileInfo = {}
        for lineIdx, lineInfo in MUTANT.lineIdx2lineKey.items():
            target_file = lineInfo["file"]
            line_num = lineInfo["lineno"]
            # TODO: HERE WE HAVE STARTED FROM SUBJECT_REPO BECAUSE ZLIB_NG's LINE_INFO CONTAINS FROM REPO ROOT
            target_file_path = os.path.join(self.subject_repo, target_file)
            if target_file not in targetFiles2fileInfo:
                targetFiles2fileInfo[target_file] = {"line_nums": [], "target_file_path": target_file_path}
            targetFiles2fileInfo[target_file]["line_nums"].append(str(line_num))
        return targetFiles2fileInfo

    def _generate_mutants_for_target_files_only_only_selected_lines(self, targetFiles2fileInfo: dict):
        # 1. set compile_commands.json path
        compile_command_path = os.path.join(self.core_dir, self.SUBJECT.subject_configs["compile_command_path"])

        # 2. generate mutants for each target file on the selected lines
        for target_file, targetFileInfo in targetFiles2fileInfo.items():
            line_nums_str = ",".join(targetFileInfo["line_nums"])
            target_file_path = targetFileInfo["target_file_path"]

            target_file_mutant_dir_name = target_file.replace("/", "#")
            target_file_mutant_dir_path = os.path.join(self.version_mutant_mutants_dir, target_file_mutant_dir_name)

            cmd = [
                self.musicup_exec, 
                str(target_file_path),
                "-o", str(target_file_mutant_dir_path),
                "-ll", str(self.CONFIG.ENV["LIMIT_ON_LINE"]), # limit on line
                "-l", str(self.CONFIG.ENV["LIMIT_ON_MUT_OP"]), # limit on mutation operator
                "-d", UNUSED_OPS, # unused operators
                "-i", line_nums_str, # executed lines
                "-p", str(compile_command_path), # compile_commands.json path
            ]
            execute_command_as_list(cmd)
            LOGGER.info(f"Mutants generated for {target_file} on lines {line_nums_str} in {target_file_mutant_dir_path}")
    
    def _get_generated_mutants(self, targetFile2fileInfo: dict):
        mutant_list = []

        extension = "*.c" if self.SUBJECT.subject_configs["subject_language"] == "C" else "*.cpp"

        for target_file, targetFileInfo in targetFile2fileInfo.items():
            target_file_mutant_dir_name = target_file.replace("/", "#")
            target_file_mutant_dir_path = os.path.join(self.version_mutant_mutants_dir, target_file_mutant_dir_name)
            target_mutants = list(Path(target_file_mutant_dir_path).glob(extension))
            for mutant in target_mutants:
                mutant_list.append((target_file, mutant))
        return mutant_list

    def _get_mutation_info_record(self, targetFile2fileInfo: dict, MUTANT: Mutant = None):
        mutation_info_record = {}

        for target_file, targetFileInfo in targetFile2fileInfo.items():
            target_file_mutant_dir_name = target_file.replace("/", "#")
            target_file_mutant_dir_path = os.path.join(self.version_mutant_mutants_dir, target_file_mutant_dir_name)
            target_file_source_filename = ".".join(os.path.basename(target_file).split(".")[:-1]) # remove extension
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
                    pre_start_line = int(row[2])
                    lineIdx = MUTANT.filename2lineNum2lineIdx[target_file][pre_start_line]

                    mutation_info_record[target_file][mut_name] = {
                        "mut_op": op,
                        "line_idx": lineIdx
                    }
        return mutation_info_record
    
    def _insert_generated_mutants_into_db(self, generated_mutants: list, mutation_info_record: dict, MUTANT: Mutant):
        mut_idx = -1
        for target_file, mutant_path in generated_mutants:
            mutant_filename = os.path.basename(mutant_path)
            if mutant_filename not in mutation_info_record[target_file]:
                LOGGER.error(f"Mutant {mutant_filename} not found in mutation info record for target file {target_file}")
            
            mut_op = mutation_info_record[target_file][mutant_filename]["mut_op"]
            line_idx = mutation_info_record[target_file][mutant_filename]["line_idx"]

            mut_idx += 1
            values = [
                MUTANT.bug_idx,
                True,
                target_file,
                mutant_filename,
                mut_idx, # mutant_idx
                line_idx,
                mut_op,
            ]
            LOGGER.debug(f"[bugIdx{MUTANT.bug_idx}] Inserting mutant into DB: {values}")

            self.DB.insert(
                "cpp_mutation_info",
                "bug_idx, is_for_test, targetting_file, mutant_filename, mutant_idx, line_idx, mut_op",
                values
            )
            LOGGER.debug(f"Inserted mutant {mutant_filename} into DB for bug_idx {MUTANT.bug_idx}")
        self.update_status_column_in_db(MUTANT.bug_idx, "selected_for_mbfl")
        self.update_status_column_in_db(MUTANT.bug_idx, "mutants_generated")


    def stop(self):
        """Stop the mutant generation process"""
        LOGGER.info("Stopping Mutant Generator Worker")
        super().stop()

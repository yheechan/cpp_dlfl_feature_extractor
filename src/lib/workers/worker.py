from abc import ABC, abstractmethod
import logging
import os

from lib.experiment_configs import ExperimentConfigs
from lib.subject import Subject
from lib.factories.file_manager_factory import FileManagerFactory
from lib.database import CRUD
from lib.mutant import Mutant
from lib.worker_context import WorkerContext

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class Worker(ABC):
    def __init__(self, CONFIG: ExperimentConfigs):
        self.CONFIG = CONFIG
        self.SUBJECT = Subject(self.CONFIG.ARGS.subject)
        self.FILE_MANAGER = FileManagerFactory.create_file_manager(
            self.CONFIG.ARGS.is_remote
        )
        self.DB = self._create_db()

        # Initialize all paths
        self._initialize_paths()

        # Set up all directories
        self._set_directories()

        # Create context for executors with updated paths
        self.CONTEXT = self._create_context()
    
    def _initialize_paths(self):
        """Initialize all directory and file paths"""
        self.log_dir = None
        self.out_dir = None
        self.working_dir = None
        self.working_env_dir = None
        self.subject_repo = None
        self.testcases_dir = None
        self.tools_dir = None
        self.musicup_exec = None
        self.extractor_exec = None

    def _create_db(self) -> CRUD:
        """Create a CRUD object for database interactions"""
        return CRUD(
            host=self.CONFIG.ENV["DB_HOST"],
            port=self.CONFIG.ENV["DB_PORT"],
            user=self.CONFIG.ENV["DB_USER"],
            password=self.CONFIG.ENV["DB_PASSWORD"],
            database=self.CONFIG.ENV["DB"]
        )

    def _create_context(self) -> WorkerContext:
        return WorkerContext(
            CONFIG=self.CONFIG,
            FILE_MANAGER=self.FILE_MANAGER,
            SUBJECT=self.SUBJECT,
            tools_dir=self.tools_dir,
            log_dir=self.log_dir,
            out_dir=self.out_dir,
            working_dir=self.working_dir,
            working_env_dir=self.working_env_dir,
            subject_repo=self.subject_repo,
            testcases_dir=self.testcases_dir,
            coverage_dir=self.coverage_dir,
            line2function_dir=self.line2function_dir,
            mutant_mutants_dir=self.mutant_mutants_dir,
            musicup_exec=self.musicup_exec,
            extractor_exec=self.extractor_exec
        )
    
    def _set_directories(self):
        LOGGER.debug("Setting up subject directories")
        # subject research directories
        self.log_dir = os.path.join(
            self.CONFIG.ENV["ROOT_DIR"],
            "logs",
            self.CONFIG.ARGS.experiment_label,
            self.CONFIG.ARGS.subject,
            "workers",
            self.CONFIG.ARGS.worker_type,
        )
        LOGGER.debug(f"Subject log directory: {self.log_dir}")  
        self.out_dir = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"],
            self.CONFIG.ARGS.experiment_label,
            self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject output directory: {self.out_dir}")
        self.working_dir = os.path.join(
            self.CONFIG.ENV["HOME_DIR"],
            "cpp_research_working_dir",
            self.CONFIG.ARGS.experiment_label,
            self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject working directory: {self.working_dir}")
        
        self.tools_dir = os.path.join(self.working_dir, "tools")
        LOGGER.debug(f"Subject tools directory: {self.tools_dir}")
        self.musicup_exec = os.path.join(self.tools_dir, "music")
        self.extractor_exec = os.path.join(self.tools_dir, "extractor")
        LOGGER.debug("Tool executables copied to tools directory")

        self.working_env_dir = os.path.join(self.working_dir, "working_env")
        LOGGER.debug(f"Subject working environment directory: {self.working_env_dir}")

        # core directory
        self.core_dir = os.path.join(
            self.working_env_dir, self.CONFIG.ARGS.machine,
            f"core{self.CONFIG.ARGS.core_idx}"
        )

        # subject repository directories
        self.subject_repo = os.path.join(
            self.core_dir, self.CONFIG.ARGS.subject
        )
        self.SUBJECT.set_files(self.subject_repo)
        self.SUBJECT.check_required_scripts_exists()
        self.SUBJECT.set_subject_configurations()
        LOGGER.debug(f"Subject repository: {self.subject_repo}")

        self.testcases_dir = os.path.join(self.subject_repo, "testcases")
        LOGGER.debug(f"Subject testcases directory: {self.testcases_dir}")

        self.patch_dir = os.path.join(self.core_dir, "patches")
        if not os.path.exists(self.patch_dir):
            os.makedirs(self.patch_dir, exist_ok=True)
        LOGGER.debug(f"Patch directory: {self.patch_dir}")

        # coverage directory
        self.coverage_dir = os.path.join(self.core_dir, "coverage")
        LOGGER.debug(f"Coverage directory: {self.coverage_dir}")

        # line2function out dir
        self.line2function_dir = os.path.join(self.out_dir, "line2function")
        if not os.path.exists(self.line2function_dir):
            os.makedirs(self.line2function_dir, exist_ok=True)
        LOGGER.debug(f"Line2Function output directory: {self.line2function_dir}")

        # mutant mutant out dir
        self.mutant_mutants_dir = os.path.join(self.out_dir, "mutant_mutants")
        if not os.path.exists(self.mutant_mutants_dir):
            os.makedirs(self.mutant_mutants_dir, exist_ok=True)
        LOGGER.debug(f"MutantMutant output directory: {self.mutant_mutants_dir}")

    def update_status_column_in_db(self, bug_idx: int, col_key: str):
        self.DB.update(
            "cpp_bug_info",
            set_values={col_key: True},
            conditions={"bug_idx": bug_idx}
        )
        LOGGER.debug(f"Updated bug_idx {bug_idx} to status {col_key} in DB")

    @abstractmethod
    def execute(self):
        """Execute the worker's main functionality"""
        raise NotImplementedError("Subclasses must implement execute() method")

    def stop(self):
        """Optional stop method that subclasses can override"""
        pass


    def make_mutant(self):
        # set MUTANT
        target_file = self.CONFIG.ARGS.target_file
        target_file_path = os.path.join(self.core_dir, target_file)
        if not os.path.exists(target_file_path):
            LOGGER.error(f"Target file {target_file_path} does not exist")
            return

        mutant_file = self.CONFIG.ARGS.mutant
        mutant_file_path = os.path.join(self.core_dir, f"{self.CONFIG.STAGE}-assigned_works", mutant_file)
        if not os.path.exists(mutant_file_path):
            LOGGER.error(f"Mutant file {mutant_file_path} does not exist")
            return
    
        # 1. Patch target_file with mutant_file
        patch_file = os.path.join(self.patch_dir, f"{self.CONFIG.ARGS.mutant}.patch")
        MUTANT = Mutant(
            self.CONFIG.ARGS.subject,
            self.CONFIG.ARGS.experiment_label,
            target_file, target_file_path, 
            mutant_file, mutant_file_path,
            patch_file, self.subject_repo
        )
        res = MUTANT.make_patch_file()
        if not res:
            LOGGER.error(f"Failed to create patch file {patch_file}, skipping mutant")
            return
        LOGGER.info(f"Patch file created at {patch_file}")
        return MUTANT

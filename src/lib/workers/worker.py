from abc import ABC, abstractmethod
import logging
import os
import subprocess as sp

from lib.experiment_configs import ExperimentConfigs
from lib.subject import Subject
from lib.factories.file_manager_factory import FileManagerFactory
from lib.database import CRUD

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class Worker(ABC):
    def __init__(self, CONFIG: ExperimentConfigs):
        self.CONFIG = CONFIG
        self.SUBJECT = Subject(self.CONFIG)
        self.FILE_MANAGER = FileManagerFactory.create_file_manager(
            self.CONFIG.ARGS.is_remote
        )
        self.DB = self._create_db()

        # Initialize all paths
        self._initialize_paths()

        # Set up all directories
        self._set_directories()
    
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
            os.makedirs(self.patch_dir)
        LOGGER.debug(f"Patch directory: {self.patch_dir}")


    @abstractmethod
    def execute(self):
        """Execute the worker's main functionality"""
        raise NotImplementedError("Subclasses must implement execute() method")

    def stop(self):
        """Optional stop method that subclasses can override"""
        pass

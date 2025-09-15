from abc import ABC, abstractmethod
import os
import logging
from pathlib import Path
import json

from lib.experiment_configs import ExperimentConfigs
from lib.subject import Subject
from lib.factories.file_manager_factory import FileManagerFactory
from lib.factories.executor_factory import ExecutorFactory
from lib.engine_context import EngineContext
from lib.database import CRUD

LOGGER = logging.getLogger(__name__)

class Engine(ABC):
    def __init__(self, CONFIG: ExperimentConfigs):
        self.CONFIG = CONFIG
        self.SUBJECT = Subject(self.CONFIG.ARGS.subject)
        self.FILE_MANAGER = FileManagerFactory.create_file_manager(
            self.CONFIG.ARGS.is_remote
        )
        self.EXECUTOR = ExecutorFactory.create_executor(
            self.CONFIG.ARGS.is_remote
        )
        self.DB = self._create_db()

        # Initialize all paths
        self._initialize_paths()
        
        if not self.CONFIG.ARGS.engine_type == "dataset_postprocessor":
            # Set up all directories
            self._set_directories()

            # Initialize local directories and executables first
            self._initialize_basic_directory_on_local()

            # Create context for executors with updated paths
            self.CONTEXT = self._create_context()

            # Initialize directories for machines
            self._initialize_basic_directory_for_machines()
        else:
            self.CONTEXT = self._create_context()
    
    def _initialize_paths(self):
        """Initialize all directory and file paths"""
        self.log_dir = None
        self.out_dir = None
        self.working_dir = None
        self.working_env_dir = None
        self.src_repo = None
        self.dest_repo = None
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
    
    def _create_context(self) -> EngineContext:
        """Create an EngineContext object with all necessary data"""
        return EngineContext(
            CONFIG=self.CONFIG,
            FILE_MANAGER=self.FILE_MANAGER,
            tools_dir=self.tools_dir,
            log_dir=self.log_dir,
            out_dir=self.out_dir,
            working_dir=self.working_dir,
            working_env_dir=self.working_env_dir,
            dest_repo=self.dest_repo,
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
            self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject log directory: {self.log_dir}")  
        self.config_dir = os.path.join(
            self.CONFIG.ENV["ROOT_DIR"],
            "configs",
        )
        LOGGER.debug(f"Config directory: {self.config_dir}")
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
        self.working_env_dir = os.path.join(self.working_dir, "working_env")
        LOGGER.debug(f"Subject working environment directory: {self.working_env_dir}")
        
        # subject repository directories
        self.src_repo = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"], "subject_repositories", self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject source repository: {self.src_repo}")
        self.dest_repo = os.path.join(
            self.working_dir, self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject destination repository: {self.dest_repo}")
        self.testcases_dir = os.path.join(self.dest_repo, "testcases")
        LOGGER.debug(f"Subject testcases directory: {self.testcases_dir}")

    def _initialize_basic_directory_on_local(self):
        """Set up the basic working directory structure on the local machine"""
        LOGGER.debug("Initializing basic directory structure on local machine")
        # Setup tools
        self.tools_dir = os.path.join(self.working_dir, "tools")
        self.FILE_MANAGER.make_directory(self.tools_dir)
        LOGGER.debug(f"Tools directory created at: {self.tools_dir}")

        src_musicup_exec = os.path.join(self.CONFIG.ENV["ROOT_DIR"], "tools/MUSICUP/music")
        src_extractor_exec = os.path.join(self.CONFIG.ENV["ROOT_DIR"], "tools/extractor/extractor")
        assert os.path.exists(src_musicup_exec), "MUSICUP executable does not exist"
        assert os.path.exists(src_extractor_exec), "Extractor executable does not exist"

        self.FILE_MANAGER.copy_file(src_musicup_exec, self.tools_dir)
        self.FILE_MANAGER.copy_file(src_extractor_exec, self.tools_dir)
        self.musicup_exec = os.path.join(self.tools_dir, "music")
        self.extractor_exec = os.path.join(self.tools_dir, "extractor")
        LOGGER.debug("Tool executables copied to tools directory")

        # Setup subject repository
        self.FILE_MANAGER.copy_directory(self.src_repo, self.dest_repo)
        if self.SUBJECT.name is not None:
            self.SUBJECT.set_files(self.dest_repo)
            self.SUBJECT.check_required_scripts_exists()
            self.SUBJECT.set_subject_configurations()
        LOGGER.debug("Subject repository copied to working directory")

        # Setup subject log dir
        self.FILE_MANAGER.make_directory(self.log_dir)
        LOGGER.debug(f"Subject log directory created at: {self.log_dir}")

        # Setup subject out dir
        self.FILE_MANAGER.make_directory(self.out_dir)
        LOGGER.debug(f"Subject output directory created at: {self.out_dir}")

    def _initialize_basic_directory_for_machines(self):
        """Initialize directory structure for execution environment"""
        self.EXECUTOR.prepare_for_execution(self.CONTEXT)
        LOGGER.debug("Basic directory structure initialized for execution")

    @abstractmethod
    def run(self):
        """Execute the engine's main functionality"""
        raise NotImplementedError("Subclasses must implement run() method")
    
    def cleanup(self):
        """Optional cleanup method that subclasses can override"""
        pass

    def get_target_mutants(self, special: str = None) -> list:
        """Get the list of target mutants to process"""
        self.generated_mutants_dir = os.path.join(self.out_dir, "generated_mutants")
        res = self.DB.read(
            "cpp_bug_info",
            columns="version, type, target_code_file, buggy_code_file, bug_idx",
            conditions={
                "subject": self.CONFIG.ARGS.subject,
                "experiment_label": self.CONFIG.ARGS.experiment_label,
            },
            special=special
        )
        
        mutant_list = []
        for version, mutant_type, target_code_file, buggy_code_file, bug_idx in res:
            target_file_mutant_dir_name = target_code_file.replace("/", "#")
            target_file_mutant_dir_path = os.path.join(self.generated_mutants_dir, target_file_mutant_dir_name)
            mutant = Path(os.path.join(target_file_mutant_dir_path, buggy_code_file))
            mutant_list.append((target_code_file, mutant, target_file_mutant_dir_path, bug_idx))

        LOGGER.info(f"Total mutants to test: {len(mutant_list)}")
        return mutant_list

    def set_experiment_setup_configs(self):
        experiment_setup_config_path = os.path.join(
            self.config_dir,
            "experiment_setup.rq0.json"
        )
        if not os.path.exists(experiment_setup_config_path):
            LOGGER.error(f"Experiment setup config file not found at {experiment_setup_config_path}")
            raise FileNotFoundError(f"Config file not found: {experiment_setup_config_path}")

        exp_config = json.load(open(experiment_setup_config_path, 'r'))
        for key, value in exp_config.items():
            # set to self.CONFIG.ENV if not already set
            if key not in self.CONFIG.ENV:
                self.CONFIG.ENV[key] = value

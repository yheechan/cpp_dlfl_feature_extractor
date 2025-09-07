from abc import ABC, abstractmethod
import os
import logging

from lib.experiment_configs import ExperimentConfigs
from lib.subject import Subject
from lib.factories.file_manger_factory import FileManagerFactory

LOGGER = logging.getLogger(__name__)

class Engine(ABC):
    def __init__(self, CONFIG: ExperimentConfigs):
        self.CONFIG = CONFIG
        self.SUBJECT = Subject(self.CONFIG)
        self.FILE_MANAGER = FileManagerFactory.create_file_manager(
            self.CONFIG.ARGS.is_remote
        )
        self.musicup_exec = None
        self.extractor_exec = None

        self.initialize_basic_directory_on_local()

    @abstractmethod
    def run(self):
        """Execute the engine's main functionality"""
        raise NotImplementedError("Subclasses must implement run() method")
    
    def cleanup(self):
        """Optional cleanup method that subclasses can override"""
        pass

    def initialize_basic_directory_on_local(self):
        """Set up the basic working directory structure on the local machine"""
        LOGGER.debug("Initializing basic directory structure on local machine")
        # Setup tools
        tools_dir = os.path.join(self.SUBJECT.working_dir, "tools")
        self.FILE_MANAGER.make_directory(tools_dir)
        LOGGER.debug(f"Tools directory created at: {tools_dir}")

        src_musicup_exec = os.path.join(self.CONFIG.ROOT_DIR, "tools/MUSICUP/music")
        src_extractor_exec = os.path.join(self.CONFIG.ROOT_DIR, "tools/extractor/extractor")
        assert os.path.exists(src_musicup_exec), "MUSICUP executable does not exist"
        assert os.path.exists(src_extractor_exec), "Extractor executable does not exist"

        self.FILE_MANAGER.copy_file(src_musicup_exec, tools_dir)
        self.FILE_MANAGER.copy_file(src_extractor_exec, tools_dir)
        LOGGER.debug("Tool executables copied to tools directory")

        # Setup subject repository
        self.FILE_MANAGER.copy_directory(self.SUBJECT.src_repo, self.SUBJECT.dest_repo)
        self.SUBJECT.check_required_scripts_exists()
        LOGGER.debug("Subject repository copied to working directory")

        # Setup subject log dir
        self.FILE_MANAGER.make_directory(self.SUBJECT.log_dir)
        LOGGER.debug(f"Subject log directory created at: {self.SUBJECT.log_dir}")

        # Setup subject out dir
        self.FILE_MANAGER.make_directory(self.SUBJECT.out_dir)
        LOGGER.debug(f"Subject output directory created at: {self.SUBJECT.out_dir}")

        # Set up subject working dir
        self.FILE_MANAGER.make_directory(self.SUBJECT.working_dir)
        LOGGER.debug(f"Subject working directory created at: {self.SUBJECT.working_dir}")

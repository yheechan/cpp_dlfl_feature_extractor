from abc import ABC, abstractmethod

from lib.experiment_configs import ExperimentConfigs
from utils.file_utils import *

class FileManager(ABC):
    """Abstract base class for file managers"""

    def initialize_working_directory_on_local(self, config: ExperimentConfigs):
        """Set up the working directory for file operations"""
        self.copy_subject_repository_to_working_dir(config)
        self.configurate_tools_directory(config)
        self.copy_tools_executables(config)

    def copy_subject_repository_to_working_dir(self, config: ExperimentConfigs):
        src_repo = os.path.join(config.RESEARCH_DATA, "subject_repositories", config.ARGS.subject)
        dest_repo = os.path.join(config.WORKING_DIR, config.ARGS.subject)
        copy_directory(src_repo, dest_repo)
        self.check_required_scripts_exists(dest_repo)

    def check_required_scripts_exists(self, dest_repo: str):
        configure_no_cov_file = os.path.join(dest_repo, "configure_no_cov_script.sh")
        configure_yes_cov_file = os.path.join(dest_repo, "configure_yes_cov_script.sh")
        build_file = os.path.join(dest_repo, "build_script.sh")
        clean_file = os.path.join(dest_repo, "clean_script.sh")
        assert os.path.exists(configure_no_cov_file), "Configure script does not exist"
        assert os.path.exists(configure_yes_cov_file), "Configure script does not exist"
        assert os.path.exists(build_file), "Build script does not exist"
        assert os.path.exists(clean_file), "Clean build script does not exist"

    def configurate_tools_directory(self, config: ExperimentConfigs):
        tools_dir = os.path.join(config.WORKING_DIR, "tools")
        make_directory(tools_dir)

    def copy_tools_executables(self, config: ExperimentConfigs):
        musicup_exec = os.path.join(config.ROOT_DIR, "tools/MUSICUP/music")
        extractor_exec = os.path.join(config.ROOT_DIR, "tools/extractor/extractor")
        assert os.path.exists(musicup_exec), "MUSICUP executable does not exist"
        assert os.path.exists(extractor_exec), "Extractor executable does not exist"
        dest_tools_dir = os.path.join(config.WORKING_DIR, "tools")
        copy_file(musicup_exec, dest_tools_dir)
        copy_file(extractor_exec, dest_tools_dir)

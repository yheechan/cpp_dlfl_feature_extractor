import os
import json
import logging

from lib.experiment_configs import ExperimentConfigs

LOGGER = logging.getLogger(__name__)

class Subject():
    def __init__(self, CONFIG: ExperimentConfigs):
        self.CONFIG = CONFIG
        self.name = CONFIG.ARGS.subject
        self.set_directories()
        self.set_files()
        self.set_subject_configurations()
        LOGGER.info("Subject initialized")
        self.out_dir = os.path.join(
            self.CONFIG.RESEARCH_DATA,
            self.CONFIG.ARGS.experiment_label,

        )

    def set_directories(self):
        LOGGER.debug("Setting up subject directories")
        # subject research directories
        self.log_dir = os.path.join(
            self.CONFIG.ROOT_DIR, 
            "logs",
            self.CONFIG.ARGS.experiment_label,
            self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject log directory: {self.log_dir}")  
        self.out_dir = os.path.join(
            self.CONFIG.RESEARCH_DATA,
            self.CONFIG.ARGS.experiment_label,
            self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject output directory: {self.out_dir}")
        self.working_dir = os.path.join(
            self.CONFIG.HOME_DIR,
            "cpp_research_working_dir",
            self.CONFIG.ARGS.experiment_label,
            self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject working directory: {self.working_dir}")

        # subject repository directories
        self.src_repo = os.path.join(
            self.CONFIG.RESEARCH_DATA, "subject_repositories", self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject source repository: {self.src_repo}")
        self.dest_repo = os.path.join(
            self.working_dir, self.CONFIG.ARGS.subject
        )
        LOGGER.debug(f"Subject destination repository: {self.dest_repo}")
        self.testcases_dir = os.path.join(self.dest_repo, "testcases")
        LOGGER.debug(f"Subject testcases directory: {self.testcases_dir}")
    
    def set_files(self):
        LOGGER.debug("Setting up subject files")
        self.configure_no_cov_file = os.path.join(self.dest_repo, "configure_no_cov_script.sh")
        self.configure_yes_cov_file = os.path.join(self.dest_repo, "configure_yes_cov_script.sh")
        self.build_file = os.path.join(self.dest_repo, "build_script.sh")
        self.clean_file = os.path.join(self.dest_repo, "clean_script.sh")
        self.configurations_json = os.path.join(self.dest_repo, "configurations.json")

    def set_subject_configurations(self):
        src_configuration_json = os.path.join(
            self.src_repo, "configurations.json"
        )
        self.subject_configs = json.load(open(src_configuration_json, 'r'))

    def check_required_scripts_exists(self):
        assert os.path.exists(self.configure_no_cov_file), "Configure script does not exist"
        assert os.path.exists(self.configure_yes_cov_file), "Configure script does not exist"
        assert os.path.exists(self.build_file), "Build script does not exist"
        assert os.path.exists(self.clean_file), "Clean build script does not exist"
        assert os.path.exists(self.configurations_json), "Configuration JSON does not exist"
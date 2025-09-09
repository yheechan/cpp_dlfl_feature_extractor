import os
import json
import logging

from lib.experiment_configs import ExperimentConfigs

LOGGER = logging.getLogger(__name__)

class Subject():
    def __init__(self, CONFIG: ExperimentConfigs):
        self.CONFIG = CONFIG
        self.name = CONFIG.ARGS.subject
        LOGGER.info("Subject initialized")
    
    def set_files(self, repo_dir: str = None):
        LOGGER.debug("Setting up subject files")
        self.repo_dir = repo_dir
        self.configure_no_cov_script = os.path.join(self.repo_dir, "configure_no_cov_script.sh")
        self.configure_yes_cov_script = os.path.join(self.repo_dir, "configure_yes_cov_script.sh")
        self.build_script = os.path.join(self.repo_dir, "build_script.sh")
        self.clean_script = os.path.join(self.repo_dir, "clean_script.sh")
        self.configurations_json = os.path.join(self.repo_dir, "configurations.json")

    def set_subject_configurations(self):
        self.subject_configs = json.load(open(self.configurations_json, 'r'))
        self.compile_commands_json_path = os.path.join(os.path.dirname(self.repo_dir), self.subject_configs["compile_command_path"])

    def check_required_scripts_exists(self):
        assert os.path.exists(self.configure_no_cov_script), "Configure script does not exist"
        assert os.path.exists(self.configure_yes_cov_script), "Configure script does not exist"
        assert os.path.exists(self.build_script), "Build script does not exist"
        assert os.path.exists(self.clean_script), "Clean build script does not exist"
        assert os.path.exists(self.configurations_json), "Configuration JSON does not exist"

    def set_environmental_variables(self, core_dir: str):
        if self.subject_configs["environment_setting"]["needed"]:
            for key, value in self.subject_configs["environment_setting"]["variables"].items():
                path = os.path.join(core_dir, value)
                
                if key not in os.environ:
                    os.environ[key] = path
                else:
                    os.environ[key] = f"{path}:{os.environ[key]}"
                LOGGER.debug(f"Environment variable {key} set to {os.environ[key]}")
        LOGGER.debug("Subject environmental variables set")

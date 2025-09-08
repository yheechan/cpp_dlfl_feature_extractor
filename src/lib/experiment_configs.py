import argparse
import os
import json

class ExperimentConfigs:
    # def __init__(self, args: argparse.Namespace):
    def __init__(self):
        self.ENV = None

    # def __str__(self):
        # return (f"ExperimentConfigs(verbose={self.verbose}, debug={self.debug}, "
        #         f"experiment_label='{self.experiment_label}', is_remote={self.is_remote}, "
        #         f"subject='{self.subject}', engine_type='{self.engine_type}', "
        #         f"working_directory='{self.working_directory}')")
    
    def set_parser(self) -> argparse.ArgumentParser:
        self.PARSER = argparse.ArgumentParser(
            description="C++ Deep-Learning-Based FL Feature Extractor"
        )

        # Logging and Debugging Options
        self.PARSER.add_argument(
            "-v", "--verbose",
            action="store_true",
            help="Increase output verbosity"
        )
        self.PARSER.add_argument(
            "-d", "--debug",
            action="store_true",
            help="Enable debug mode"
        )

        # Basic Configuration
        self.PARSER.add_argument(
            "-el", "--experiment-label",
            type=str,
            default="default_experiment",
            required=True,
            help="Label for the experiment (used in logging and output directories)"
        )

        self.PARSER.add_argument(
            "-ir", "--is-remote",
            action="store_true",
            default=False,
            help="Indicate if the execution is remote"
        )

        # Required Information (e.g., subject)
        self.PARSER.add_argument(
            "-s", "--subject",
            type=str,
            required=True,
            help="Specify the subject for the experiment"
        )

        # Function Selection
        self.PARSER.add_argument(
            "-et", "--engine-type",
            type=str,
            help="Specify the engine type to execute"
        )

        self.PARSER.add_argument(
            "-wt", "--worker-type",
            type=str,
            help="Specify the worker type to execute"
        )

        self.ARGS = self.PARSER.parse_args()

    def set_machine_status(self):
        machine_settings = os.path.join(self.ENV["ROOT_DIR"], ".machine_settings")
        assert os.path.exists(machine_settings), f"Machine settings file does not exist: {machine_settings}"

        settings = json.load(open(machine_settings, 'r'))
        self.MACHINE_LIST = list(settings.keys())
        self.MACHINE_CORE_LIST = []
        for machine_name, machine_info in settings.items():
            num_cores = machine_info["cores"]
            home_directory = machine_info["homedirectory"]

            for idx in range(num_cores):
                self.MACHINE_CORE_LIST.append((machine_name, idx, home_directory))

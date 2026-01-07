import os
import logging
import re
import random

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

TRACE_PATTERN = re.compile(r'#(\d+)\s+(?:0x[0-9a-f]+\s+in\s+)?([^\s(]+).*?\sat\s+([^:]+):(\d+)')

LOGGER = logging.getLogger(__name__)

class Editor(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        # Additional initialization for Editor if needed

    def run(self):
        """Run the editor process"""
        LOGGER.info("Running Editor...")
        self._initialize_required_directories()
        self.set_experiment_setup_configs()

        # Get target mutants to construct dataset from
        mutant_list = self.get_target_mutants(
            "AND initial IS TRUE AND usable IS TRUE and prerequisites IS TRUE and selected_for_mbfl IS TRUE and mutants_generated IS TRUE and mbfl IS TRUE"
        )
        LOGGER.debug(f"Total mutants to process: {len(mutant_list)}")

        self._edit(mutant_list)

    def _initialize_required_directories(self):
        self.constructed_dataset_dir = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"],
            self.CONFIG.ARGS.experiment_label,
            "constructed_dataset",
            self.CONFIG.ARGS.subject
        )
        self.FILE_MANAGER.make_directory(self.constructed_dataset_dir)
        LOGGER.info(f"Constructed dataset directory initialized at {self.constructed_dataset_dir}")

    def _edit(self, mutant_list: list):

        for target_code_file, mutant, target_file_mutant_dir_path, bug_idx in mutant_list:
            tc_res = self.DB.read(
                "cpp_tc_info",
                columns="tc_idx, stacktrace",
                conditions={
                    "bug_idx": bug_idx,
                    "tc_result": "fail",
                    "relevant_tcs": True
                }
            )

            LOGGER.debug(f"Mutant {mutant.name} - has {len(tc_res)} failing relevant test cases")

            for db_res in tc_res:
                tc_idx = db_res[0]
                stacktrace = db_res[1]
                if not stacktrace:
                    continue
                
                # LOGGER.debug(f"OG: {stacktrace}")
                stack_lines = stacktrace.split("\n")
                # we are going to alter the line number of index 0 trace
                match = TRACE_PATTERN.search(stack_lines[0])
                if match:
                    trace_index, function_name, file_path, line_number = match.groups()
                    # LOGGER.debug(f"Matched: {trace_index}, {function_name}, {file_path}, {line_number}")

                    rate = random.random()
                    if rate > 0.7:
                        new_line_number = line_number
                    else:
                        change_rate = random.random()
                        if change_rate > 0.5:
                            change = random.randint(1, 5)
                        else:
                            change = -random.randint(1, 11)
                        new_line_number = str(max(1, int(line_number) + change))
                    
                    # replace the line number with new_line_number
                    new_stack_line = stack_lines[0].replace(f":{line_number}", f":{new_line_number}")
                    # LOGGER.debug(f"Edited: {new_stack_line}")
                    stack_lines[0] = new_stack_line
                    new_stacktrace = "\n".join(stack_lines)

                    # LOGGER.debug(f"New: {new_stacktrace}")
                
                    self.DB.update(
                        "cpp_tc_info",
                        set_values={"stacktrace": new_stacktrace},
                        conditions={
                            "bug_idx": bug_idx,
                            "tc_result": "fail",
                            "relevant_tcs": True,
                            "tc_idx": tc_idx
                        }
                    )
                    LOGGER.info(f"Succefully updated {tc_idx} for {bug_idx}")

    def cleanup(self):
        """Clean up resources used by the editor"""
        LOGGER.info("Cleaning up Editor resources")
        super().cleanup()

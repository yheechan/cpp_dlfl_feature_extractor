import logging
from pathlib import Path

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class MutationTestingResultExtractor(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("MutationTestingResultExtractor initialized")
        self.mutant_mutants_dir = os.path.join(self.out_dir, "mutant_mutants")

    def run(self):
        """Run the mutation testing result extractor"""
        LOGGER.info("Running Mutation Testing Result Extractor")

        # Get target mutants to generate mutants from
        if "NSFW_c_msg" in self.CONFIG.ARGS.subject or "NSFW_cpp_thread" in self.CONFIG.ARGS.subject:
            mutant_list = self.get_target_mutants(
                "AND initial IS TRUE AND usable IS TRUE and prerequisites IS TRUE and selected_for_mbfl IS TRUE and mutants_generated IS TRUE and mbfl IS NULL",
                distinct_by_buggy_location=True
            )
        elif "NSFW_c_frw" in self.CONFIG.ARGS.subject:
            mutant_list = self.get_target_mutants(
                "AND initial IS TRUE AND usable IS TRUE and prerequisites IS TRUE and selected_for_mbfl IS TRUE and mutants_generated IS TRUE and mbfl IS TRUE",
                distinct_by_buggy_location=True
            )
            LOGGER.debug(f"mbfl is true mutants {len(mutant_list)}")
            curr_cnt = len(mutant_list)
            limit_cnt = 50 - curr_cnt
            new_mutant_list = self.get_target_mutants(
                f"AND initial IS TRUE AND usable IS TRUE and prerequisites IS TRUE and selected_for_mbfl IS TRUE and mutants_generated IS TRUE and mbfl IS NULL LIMIT {limit_cnt}",
                distinct_by_buggy_location=True
            )
            mutant_list.extend(new_mutant_list)
            LOGGER.debug(f"EXTENDED mutant list length is {len(mutant_list)}")
        else:
            mutant_list = self.get_target_mutants(
                "AND initial IS TRUE AND usable IS TRUE and prerequisites IS TRUE and selected_for_mbfl IS TRUE and mutants_generated IS TRUE and mbfl IS NULL LIMIT 10",
                distinct_by_buggy_location=True
            )
        LOGGER.debug(f"Total mutants to process: {len(mutant_list)}")

        mutant_mutants_list = self._get_mutant_mutants_from_db(mutant_list)
        LOGGER.debug(f"Testing on {len(mutant_mutants_list)} mutants")

        self._start_extracting_mutation_testing_results(mutant_mutants_list)

        # zip subject_mutant_mutants_dir
        self.FILE_MANAGER.zip_directory(self.mutant_mutants_dir, self.mutant_mutants_dir)


    def _get_mutant_mutants_from_db(self, mutant_list: list) -> list:
        """Retrieve mutant mutants from the database based on the given mutant list"""
        mutant_mutants_list = []
        for i, (origin_target_code_file, origin_mutant_path, origin_target_file_mutant_dir_path, origin_bug_idx) in enumerate(mutant_list):
            res = self.DB.read(
                "cpp_mutation_info",
                columns="targetting_file, mutant_filename, mutant_idx",
                conditions={"bug_idx": origin_bug_idx},
                special=" AND build_result IS NULL"
            )
            for new_target_code_file, new_mutant_filename, new_mutant_idx in res:
                new_target_file = new_target_code_file
                # TODO: I have change this because for zlib we save without subject prefix in mutation_info table
                # --target-file NSFW_c_frw/NSFW/src/frw/ns_event.c --mutant ns_event.MUT377.c
                if "zlib_ng" in self.CONFIG.ARGS.subject:
                    new_target_file = f"{self.CONFIG.ARGS.subject}/{new_target_code_file}"
                if "NSFW_c_" in self.CONFIG.ARGS.subject:
                    new_target_file = f"{self.CONFIG.ARGS.subject}/NSFW/src/{new_target_code_file}"
                    new_target_code_file = "NSFW/src/"+new_target_code_file
                if "NSFW_cpp_" in self.CONFIG.ARGS.subject:
                    new_target_file = f"{self.CONFIG.ARGS.subject}/NSCore/{new_target_code_file}"
                    new_target_code_file = "NSCore/"+new_target_code_file


                new_target_code_file_mutant_dir_name = new_target_code_file.replace("/", "#")
                new_target_code_file_mutant_dir_path = os.path.join(self.mutant_mutants_dir, origin_mutant_path.name, new_target_code_file_mutant_dir_name)
                new_mutant_path = Path(os.path.join(new_target_code_file_mutant_dir_path, new_mutant_filename))

                mutant_mutants_list.append((
                    origin_target_code_file,
                    new_target_file,
                    origin_mutant_path,
                    new_mutant_path,
                    origin_bug_idx,
                    new_mutant_idx
                ))
        LOGGER.info(f"Total mutant mutants to process: {len(mutant_mutants_list)}")
        return mutant_mutants_list
            
    
    def _start_extracting_mutation_testing_results(self, mutant_mutants_list: list):
        """Start the extraction of mutation testing results using the executor"""
        self.EXECUTOR.test_for_mutation_testing_results(self.CONTEXT, mutant_mutants_list)


    def cleanup(self):
        """Clean up resources used by the mutation testing result extractor"""
        LOGGER.info("Cleaning up MutationTestingResultExtractor resources")
        super().cleanup()

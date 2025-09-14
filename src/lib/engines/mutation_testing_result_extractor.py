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
        mutant_list = self.get_target_mutants("AND initial IS TRUE AND usable IS TRUE and prerequisites IS TRUE and selected_for_mbfl IS TRUE and mutants_generated IS TRUE and mbfl IS NULL")
        LOGGER.debug(f"Total mutants to process: {len(mutant_list)}")

        mutant_mutants_list = self._get_mutant_mutants_from_db(mutant_list)
        # TODO:TEMPORARILY REDUCE SET FOR TEST
        # only leave mutant where src_bug_idx == 153
        # mutant_mutants_list = [item for item in mutant_mutants_list if item[3] == 153]
        # LOGGER.debug(f"Filtered mutant mutants to process: {len(mutant_mutants_list)}")

        self._start_extracting_mutation_testing_results(mutant_mutants_list)

        # zip subject_mutant_mutants_dir
        self.FILE_MANAGER.zip_directory(self.mutant_mutants_dir, self.mutant_mutants_dir)
    

    def _get_mutant_mutants_from_db(self, mutant_list: list) -> list:
        """Retrieve mutant mutants from the database based on the given mutant list"""
        mutant_mutants_list = []
        for i, (src_target_cod_file, src_mutant_path, src_target_file_mutant_dir_path, src_bug_idx) in enumerate(mutant_list):
            res = self.DB.read(
                "cpp_mutation_info",
                columns="targetting_file, mutant_filename, mutant_idx",
                conditions={"bug_idx": src_bug_idx}
            )
            for tgt_target_code_file, tgt_mutant_filename, tgt_mutant_idx in res:
                # TODO: I have change this because for zlib we save without subject prefix in mutation_info table
                baseline_target_file = f"{self.CONFIG.ARGS.subject}/{tgt_target_code_file}"
                tgt_target_code_file_mutant_dir_name = tgt_target_code_file.replace("/", "#")
                tgt_target_code_file_mutant_dir_path = os.path.join(self.mutant_mutants_dir, src_mutant_path.name, tgt_target_code_file_mutant_dir_name)
                tgt_mutant_path = Path(os.path.join(tgt_target_code_file_mutant_dir_path, tgt_mutant_filename))

                mutant_mutants_list.append((
                    baseline_target_file,
                    src_mutant_path,
                    tgt_mutant_path,
                    src_bug_idx,
                    tgt_mutant_idx
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

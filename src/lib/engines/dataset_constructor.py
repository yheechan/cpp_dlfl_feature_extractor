import os
import logging
import json
import queue
import concurrent.futures
import pickle

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

from utils.consructor_utils import *

LOGGER = logging.getLogger(__name__)

class DatasetConstructor(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        # Additional initialization for DatasetConstructor if needed

    def run(self):
        """Run the dataset construction process"""
        LOGGER.info("Running DatasetConstructor...")
        self._initialize_required_directories()
        self._set_experiment_setup_configs()

        # Get target mutants to construct dataset from
        mutant_list = self.get_target_mutants("AND initial IS TRUE AND usable IS TRUE and prerequisites IS TRUE and selected_for_mbfl IS TRUE and mutants_generated IS TRUE and mbfl IS TRUE")
        LOGGER.debug(f"Total mutants to process: {len(mutant_list)}")

        self._write_suspicious_scores(mutant_list)

    def _initialize_required_directories(self):
        self.constructed_dataset_dir = os.path.join(
            self.CONFIG.ENV["RESEARCH_DATA"],
            self.CONFIG.ARGS.experiment_label,
            "constructed_dataset",
            self.CONFIG.ARGS.subject
        )
        self.FILE_MANAGER.make_directory(self.constructed_dataset_dir)
        LOGGER.info(f"Constructed dataset directory initialized at {self.constructed_dataset_dir}")

    def _set_experiment_setup_configs(self):
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

    def _worker(self, task_queue: queue.Queue):
        """Worker function to process mutants from the task queue"""
        while True:
            try:
                task = task_queue.get(timeout=1)
                if task is None:
                    break

                rid, mutant = task

                try:
                    LOGGER.debug(f"Worker: Starting repeat {rid}, mutant {mutant[1]}")
                    self._process_single_mutant(rid, mutant)
                    LOGGER.debug(f"Worker: Successfully processed repeat {rid}, mutant {mutant[1]}")
                except Exception as e:
                    LOGGER.error(f"Worker: Failed to process repeat {rid}, mutant {mutant[1]}: {e}")
                finally:
                    task_queue.task_done()

            except queue.Empty:
                break

    def _write_suspicious_scores(self, mutant_list: list):
        all_tasks = []
        for rid in range(1, self.CONFIG.ENV["num_repeats"]+1):
            rid_dir = os.path.join(self.constructed_dataset_dir, f"repeat_{rid}")
            if not os.path.exists(rid_dir):
                os.makedirs(rid_dir, exist_ok=True)
            for mutant in mutant_list:
                all_tasks.append((rid, mutant))

        total_task = len(all_tasks)
        LOGGER.debug(f"Created {total_task} total tasks ({self.CONFIG.ENV['num_repeats']} repeats × {len(mutant_list)} mutants)")

        core_cnt = len(self.CONFIG.MACHINE_CORE_LIST)
        task_queue = queue.Queue()
        for task in all_tasks:
            task_queue.put(task)
            LOGGER.debug(f"Added task: repeat {task[0]}, mutant {task[1][1]}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=core_cnt) as executor:
            futures = [
                executor.submit(self._worker, task_queue)
                for _ in range(core_cnt)
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    LOGGER.error(f"Error in processing mutant: {e}")

    def _process_single_mutant(self, rid: int, mutant: tuple):
        rid_dir = os.path.join(self.constructed_dataset_dir, f"repeat_{rid}")
        if not os.path.exists(rid_dir):
            os.makedirs(rid_dir, exist_ok=True)

        target_code_file, mutant, target_file_mutant_dir_path, bug_idx = mutant
        THREAD_DB = self._create_db()

        try:
            output_file = os.path.join(rid_dir, f"bug{bug_idx}--{mutant.name}--lineIdx2lineData.pkl")

            if not os.path.exists(output_file):
                lineIdx2lineData = get_lineIdx2lineData(THREAD_DB, bug_idx)
            else:
                with open(output_file, 'rb') as f:
                    lineIdx2lineData = pickle.load(f)
            
            measure_scores(
                self.CONTEXT,
                lineIdx2lineData,
                bug_idx,
                THREAD_DB, rid
            )

            with open(output_file, 'wb') as f:
                pickle.dump(lineIdx2lineData, f)
            LOGGER.debug(f"Saved lineIdx2lineData to {output_file}")
        finally:
            try:
                if hasattr(THREAD_DB, "cursor") and THREAD_DB.cursor:
                    THREAD_DB.cursor.close()
                if hasattr(THREAD_DB, "db") and THREAD_DB.db:
                    THREAD_DB.db.close()
                LOGGER.debug("Database connection closed")
            except Exception as e:
                LOGGER.error(f"Error closing database connection: {e}")

    def cleanup(self):
        """Clean up resources used by the mutant dataset constructor"""
        LOGGER.info("Cleaning up DatasetConstructor resources")
        super().cleanup()

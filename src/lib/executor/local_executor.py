import logging
import os
import concurrent.futures
import queue


from lib.executor.executor import Executor
from lib.engine_context import EngineContext
from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class LocalExecutor(Executor):
    def __init__(self):
        super().__init__()

    def prepare_for_execution(self, CONTEXT: EngineContext):
        """Set up environment for machines in local mode"""
        for machine in CONTEXT.CONFIG.MACHINE_LIST:
            CONTEXT.FILE_MANAGER.make_specific_directory(CONTEXT.working_dir, machine=machine)
            LOGGER.debug(f"Subject working directory created at: {CONTEXT.working_dir}")

            # Set up subject working env dir
            CONTEXT.FILE_MANAGER.make_specific_directory(CONTEXT.working_env_dir, machine=machine)
            LOGGER.debug(f"Subject working environment directory created at: {CONTEXT.working_env_dir}")
        
        # Set up subject working env for each machine core
        for machine_name, machine_idx, machine_home_directory in CONTEXT.CONFIG.MACHINE_CORE_LIST:
            machine_core_dir = os.path.join(CONTEXT.working_env_dir, f"{machine_name}/core{machine_idx}")
            assigned_works_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.ENV['STAGE']}-assigned_works")
            CONTEXT.FILE_MANAGER.make_specific_directory(assigned_works_dir, machine=machine_name)
            LOGGER.debug(f"Assigned works directory created at: {assigned_works_dir}")

            # Copy subject repository to each machine core working env
            dest_repo_in_core = os.path.join(machine_core_dir, CONTEXT.CONFIG.ARGS.subject)
            CONTEXT.FILE_MANAGER.copy_specific_directory(CONTEXT.dest_repo, dest_repo_in_core, machine=machine_name)
            LOGGER.debug(f"Subject repository copied to: {dest_repo_in_core}")

    def test_for_mutant_bugs(self, CONTEXT: EngineContext, mutant_list: list):
        def _worker(task_queue, machine_info):
            machine_name, core_idx, home_directory = machine_info
            machine_core_dir = os.path.join(CONTEXT.working_env_dir, f"{machine_name}/core{core_idx}")
            assigned_works_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.ENV['STAGE']}-assigned_works")
            
            while True:
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    target_file, mutant = task
                    LOGGER.info(f"Worker {machine_name}::core{core_idx} processing mutant {mutant} for file {target_file}")

                    CONTEXT.FILE_MANAGER.copy_specific_file(mutant, assigned_works_dir)

                    cmd = [
                        "python3", "main.py",
                        "--experiment-label", CONTEXT.CONFIG.ARGS.experiment_label,
                        "--subject", CONTEXT.CONFIG.ARGS.subject,
                        "--worker-type", "mutant_bug_tester",
                        "--machine", machine_name,
                        "--core-idx", str(core_idx),
                        "--target-file", target_file,
                        "--mutant", mutant.name,
                    ]
                    if CONTEXT.CONFIG.ARGS.debug:
                        cmd.append("--debug")
                    if CONTEXT.CONFIG.ARGS.verbose:
                        cmd.append("--verbose")
                    execute_command_as_list(cmd, working_dir=CONTEXT.CONFIG.ENV["CWD"])
                    try:
                        LOGGER.debug(f"{machine_name}::core{core_idx} executing command: {' '.join(cmd)} in {home_directory}")
                    except Exception as e:
                        LOGGER.error(f"Worker {machine_name}::core{core_idx} encountered an error: {e}")
                    finally:
                        task_queue.task_done()
                except queue.Empty:
                    break
                except Exception as e:
                    LOGGER.error(f"Worker {machine_name}::core{core_idx} encountered an unexpected error: {e}")
            LOGGER.info(f"Worker {machine_name}::core{core_idx} exiting")


        core_cnt = len(CONTEXT.CONFIG.MACHINE_CORE_LIST)
        task_queue = queue.Queue()
        for i, mutant in enumerate(mutant_list):
            target_file, mutant, target_file_mutant_dir_path = mutant
            task_queue.put((target_file, mutant))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=core_cnt) as executor:
            futures = [
                executor.submit(_worker, task_queue, machine_info)
                for machine_info in CONTEXT.CONFIG.MACHINE_CORE_LIST
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    LOGGER.error(f"Error occurred during mutant testing: {e}")

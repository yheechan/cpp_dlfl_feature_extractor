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
            assigned_works_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.STAGE}-assigned_works")
            CONTEXT.FILE_MANAGER.make_specific_directory(assigned_works_dir, machine=machine_name)
            LOGGER.debug(f"Assigned works directory created at: {assigned_works_dir}")
            if CONTEXT.CONFIG.STAGE == "stage05":
                mutant_origin_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.STAGE}-mutant_origin")
                CONTEXT.FILE_MANAGER.make_specific_directory(mutant_origin_dir, machine=machine_name)

            # Copy subject repository to each machine core working env
            dest_repo_in_core = os.path.join(machine_core_dir, CONTEXT.CONFIG.ARGS.subject)
            CONTEXT.FILE_MANAGER.copy_specific_directory(CONTEXT.dest_repo, dest_repo_in_core, machine=machine_name)
            LOGGER.debug(f"Subject repository copied to: {dest_repo_in_core}")

            # make coverage directory for each core
            coverage_dir = os.path.join(machine_core_dir, "coverage")
            CONTEXT.FILE_MANAGER.make_specific_directory(coverage_dir, machine=machine_name)
            LOGGER.debug(f"Coverage directory created at: {coverage_dir}")

    # Stage01: Mutant Bug Tester
    def test_for_mutant_bugs(self, CONTEXT: EngineContext, mutant_list: list):
        """Test for mutant bugs on local cores"""
        def _worker(task_queue, machine_info):
            machine_name, core_idx, home_directory = machine_info
            machine_core_dir = os.path.join(CONTEXT.working_env_dir, f"{machine_name}/core{core_idx}")
            assigned_works_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.STAGE}-assigned_works")

            needs_configuration = True
            while True:
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    target_file, mutant = task
                    LOGGER.info(f"Worker {machine_name}::core{core_idx} processing mutant {mutant} for file {target_file}")

                    # Copy mutant file to assigned works directory
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
                    if needs_configuration:
                        cmd.append("--needs-configuration")
                        needs_configuration = False
                    

                    # Execute the command
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
            
            clean_script_dir = os.path.join(machine_core_dir, CONTEXT.SUBJECT.subject_configs["build_script_working_directory"])
            clean_script = os.path.join(clean_script_dir, "clean_script.sh")
            execute_bash_script(clean_script, clean_script_dir)
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

    # Stage02: Usable Bug Tester
    def test_for_usable_bugs(self, CONTEXT: EngineContext, mutant_list: list):
        """Test for usable bugs on local cores"""
        def _worker(task_queue, machine_info):
            machine_name, core_idx, home_directory = machine_info
            machine_core_dir = os.path.join(CONTEXT.working_env_dir, f"{machine_name}/core{core_idx}")
            assigned_works_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.STAGE}-assigned_works")
            
            clean_script_dir = os.path.join(machine_core_dir, CONTEXT.SUBJECT.subject_configs["build_script_working_directory"])
            clean_script = os.path.join(clean_script_dir, "clean_script.sh")
            execute_bash_script(clean_script, clean_script_dir)

            needs_configuration = True
            while True:
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    target_file, mutant = task
                    LOGGER.info(f"Worker {machine_name}::core{core_idx} processing mutant {mutant} for file {target_file}")

                    # Copy mutant file to assigned works directory
                    CONTEXT.FILE_MANAGER.copy_specific_file(mutant, assigned_works_dir)

                    cmd = [
                        "python3", "main.py",
                        "--experiment-label", CONTEXT.CONFIG.ARGS.experiment_label,
                        "--subject", CONTEXT.CONFIG.ARGS.subject,
                        "--worker-type", "usable_bug_tester",
                        "--machine", machine_name,
                        "--core-idx", str(core_idx),
                        "--target-file", target_file,
                        "--mutant", mutant.name,
                    ]
                    if CONTEXT.CONFIG.ARGS.debug:
                        cmd.append("--debug")
                    if CONTEXT.CONFIG.ARGS.verbose:
                        cmd.append("--verbose")
                    if needs_configuration:
                        cmd.append("--needs-configuration")
                        needs_configuration = False
                    

                    # Execute the command
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
            task_queue.put((mutant[0], mutant[1]))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=core_cnt) as executor:
            futures = [
                executor.submit(_worker, task_queue, machine_info)
                for machine_info in CONTEXT.CONFIG.MACHINE_CORE_LIST
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    LOGGER.error(f"Error occurred during usable bug testing: {e}")

    # Stage03: Prerequisite Data Tester
    def test_for_prerequisite_data(self, CONTEXT: EngineContext, mutant_list: list):
        """Test for prerequisite data on local cores"""
        def _worker(task_queue, machine_info):
            machine_name, core_idx, home_directory = machine_info
            machine_core_dir = os.path.join(CONTEXT.working_env_dir, f"{machine_name}/core{core_idx}")
            assigned_works_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.STAGE}-assigned_works")
            
            clean_script_dir = os.path.join(machine_core_dir, CONTEXT.SUBJECT.subject_configs["build_script_working_directory"])
            clean_script = os.path.join(clean_script_dir, "clean_script.sh")
            execute_bash_script(clean_script, clean_script_dir)

            needs_configuration = True
            while True:
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    target_file, mutant = task
                    LOGGER.info(f"Worker {machine_name}::core{core_idx} processing mutant {mutant} for file {target_file}")

                    # Copy mutant file to assigned works directory
                    CONTEXT.FILE_MANAGER.copy_specific_file(mutant, assigned_works_dir)

                    cmd = [
                        "python3", "main.py",
                        "--experiment-label", CONTEXT.CONFIG.ARGS.experiment_label,
                        "--subject", CONTEXT.CONFIG.ARGS.subject,
                        "--worker-type", "prerequisite_data_tester",
                        "--machine", machine_name,
                        "--core-idx", str(core_idx),
                        "--target-file", target_file,
                        "--mutant", mutant.name,
                    ]
                    if CONTEXT.CONFIG.ARGS.debug:
                        cmd.append("--debug")
                    if CONTEXT.CONFIG.ARGS.verbose:
                        cmd.append("--verbose")
                    if needs_configuration:
                        cmd.append("--needs-configuration")
                        needs_configuration = False
                    

                    # Execute the command
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
            task_queue.put((mutant[0], mutant[1]))

        with concurrent.futures.ThreadPoolExecutor(max_workers=core_cnt) as executor:
            futures = [
                executor.submit(_worker, task_queue, machine_info)
                for machine_info in CONTEXT.CONFIG.MACHINE_CORE_LIST
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    LOGGER.error(f"Error occurred during prerequisite data testing: {e}")

    # Stage04: Mutant Mutant Generator
    def generate_mutants_from_mutants(self, CONTEXT: EngineContext, mutant_list: list):
        """Generate mutants from existing mutants on local cores"""
        def _worker(task_queue, machine_info, CONTEXT: EngineContext):
            machine_name, core_idx, home_directory = machine_info
            machine_core_dir = os.path.join(CONTEXT.working_env_dir, f"{machine_name}/core{core_idx}")
            assigned_works_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.STAGE}-assigned_works")
            
            clean_script_dir = os.path.join(machine_core_dir, CONTEXT.SUBJECT.subject_configs["build_script_working_directory"])
            clean_script = os.path.join(clean_script_dir, "clean_script.sh")
            execute_bash_script(clean_script, clean_script_dir)

            needs_configuration = True
            while True:
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    target_file, mutant = task
                    LOGGER.info(f"Worker {machine_name}::core{core_idx} processing mutant {mutant} for file {target_file}")

                    # Copy mutant file to assigned works directory
                    CONTEXT.FILE_MANAGER.copy_specific_file(mutant, assigned_works_dir)

                    cmd = [
                        "python3", "main.py",
                        "--experiment-label", CONTEXT.CONFIG.ARGS.experiment_label,
                        "--subject", CONTEXT.CONFIG.ARGS.subject,
                        "--worker-type", "mutant_generator_worker",
                        "--machine", machine_name,
                        "--core-idx", str(core_idx),
                        "--target-file", target_file,
                        "--mutant", mutant.name,
                    ]
                    if CONTEXT.CONFIG.ARGS.debug:
                        cmd.append("--debug")
                    if CONTEXT.CONFIG.ARGS.verbose:
                        cmd.append("--verbose")
                    if needs_configuration:
                        cmd.append("--needs-configuration")
                        needs_configuration = False
                    

                    # Execute the command
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
            task_queue.put((mutant[0], mutant[1]))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=core_cnt) as executor:
            futures = [
                executor.submit(_worker, task_queue, machine_info, CONTEXT)
                for machine_info in CONTEXT.CONFIG.MACHINE_CORE_LIST
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    LOGGER.error(f"Error occurred during mutant generation: {e}")

    # stage05: Mutation Testing Result Tester
    def test_for_mutation_testing_results(self, CONTEXT: EngineContext, mutant_list: list):
        """Test for mutation testing results on local cores"""
        def _worker(task_queue, machine_info, CONTEXT: EngineContext):
            machine_name, core_idx, home_directory = machine_info
            machine_core_dir = os.path.join(CONTEXT.working_env_dir, f"{machine_name}/core{core_idx}")
            assigned_works_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.STAGE}-assigned_works")
            mutant_origin_dir = os.path.join(machine_core_dir, f"{CONTEXT.CONFIG.STAGE}-mutant_origin")
            
            clean_script_dir = os.path.join(machine_core_dir, CONTEXT.SUBJECT.subject_configs["build_script_working_directory"])
            clean_script = os.path.join(clean_script_dir, "clean_script.sh")
            execute_bash_script(clean_script, clean_script_dir)

            needs_configuration = True
            while True:
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    origin_target_code_file, new_target_file, \
                        origin_mutant_path, new_mutant_path, \
                        origin_bug_idx, new_mutant_idx  = task
                    LOGGER.info(f"Worker {machine_name}::core{core_idx} processing mutant {mutant} for file {new_target_file}")

                    # Copy mutant file to assigned works directory
                    CONTEXT.FILE_MANAGER.copy_specific_file(new_mutant_path, assigned_works_dir)
                    CONTEXT.FILE_MANAGER.copy_specific_file(origin_mutant_path, mutant_origin_dir)

                    # TODO: Do not forget that target_file here is from cpp_mutation_info table
                    cmd = [
                        "python3", "main.py",
                        "--experiment-label", CONTEXT.CONFIG.ARGS.experiment_label,
                        "--subject", CONTEXT.CONFIG.ARGS.subject,
                        "--worker-type", "mutation_testing_result_tester",
                        "--machine", machine_name,
                        "--core-idx", str(core_idx),
                        "--target-file", new_target_file,
                        "--mutant", new_mutant_path.name,
                        "--origin-mutant-target-file", origin_target_code_file,
                        "--origin-mutant", origin_mutant_path.name,
                        "--bug-id", str(origin_bug_idx),
                        "--mutant-id", str(new_mutant_idx)
                    ]
                    if CONTEXT.CONFIG.ARGS.debug:
                        cmd.append("--debug")
                    if CONTEXT.CONFIG.ARGS.verbose:
                        cmd.append("--verbose")
                    if needs_configuration:
                        cmd.append("--needs-configuration")
                        needs_configuration = False
                    

                    # Execute the command
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
            task_queue.put((mutant[0], mutant[1], mutant[2], mutant[3], mutant[4], mutant[5]))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=core_cnt) as executor:
            futures = [
                executor.submit(_worker, task_queue, machine_info, CONTEXT)
                for machine_info in CONTEXT.CONFIG.MACHINE_CORE_LIST
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    LOGGER.error(f"Error occurred during mutation testing result extraction: {e}")

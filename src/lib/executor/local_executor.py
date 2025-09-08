import logging
import os

from lib.executor.executor import Executor
from lib.engine_context import EngineContext

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

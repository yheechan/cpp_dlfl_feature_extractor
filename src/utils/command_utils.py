import os
import subprocess as sp
import logging

LOGGER = logging.getLogger(__name__)

def execute_bash_script(script_path: str, working_dir: str = None) -> int:
    """Execute a bash script located at script_path within the specified working directory."""
    if not os.path.exists(script_path):
        LOGGER.error(f"Script does not exist: {script_path}")
        return -1

    try:
        result = sp.run(['bash', script_path], cwd=working_dir, check=True, stderr=sp.PIPE, stdout=sp.DEVNULL)
        LOGGER.info(f"Script executed successfully: {script_path}")
        return 0
    except sp.CalledProcessError as e:
        LOGGER.error(f"Error executing script: {script_path}")
        LOGGER.error(f"Return code: {e.returncode}")
        LOGGER.error(f"Error output: {e.stderr.decode().strip()}")
        return e.returncode

def execute_command_as_list(command: list, working_dir: str = None) -> int:
    """Execute a command represented as a list within the specified working directory."""
    if not command or not isinstance(command, list):
        LOGGER.error("Command must be a non-empty list")
        return -1

    try:
        result = sp.run(command, cwd=working_dir, check=True, stderr=sp.PIPE, stdout=sp.DEVNULL)
        LOGGER.info(f"Command executed successfully: {' '.join(command)}")
        return 0
    except sp.CalledProcessError as e:
        LOGGER.error(f"Error executing command: {' '.join(command)}")
        LOGGER.error(f"Return code: {e.returncode}")
        LOGGER.error(f"Error output: {e.stderr.decode().strip()}")
        return e.returncode
import subprocess as sp
import os
import logging

LOGGER = logging.getLogger(__name__)


class Mutant:
    def __init__(self, target_file: str = None, mutant_file: str = None, patch_file: str = None):
        self.target_file = target_file
        self.mutant_file = mutant_file
        self.patch_file = patch_file
        self.mutant_name = os.path.basename(mutant_file)
        self.mutant_type = None

    def make_path_file(self):
        cmd = ["diff", self.target_file, self.mutant_file]
        try:
            res = sp.run(cmd, stdout=open(self.patch_file, 'w'))
            if res.returncode not in [0, 1]:  # diff returns 0 if no differences, 1 if differences found
                LOGGER.error(f"Error creating patch file with command: {' '.join(cmd)}")
                return False
            return True
        except Exception as e:
            LOGGER.error(f"Error executing command: {' '.join(cmd)}")
            raise e

    def apply_patch(self, revert=False):
        if revert:
            cmd = ["patch", "-R", "-i", self.patch_file, self.target_file]
        else:
            cmd = ["patch", "-i", self.patch_file, self.target_file]

        try:
            res = sp.run(cmd, stdout=sp.DEVNULL, stderr=sp.PIPE)
            if res.returncode != 0:
                LOGGER.error(f"Error applying patch with command: {' '.join(cmd)}")
                LOGGER.error(f"Error output: {res.stderr.decode().strip()}")
                return False
            LOGGER.debug(f"Patch applied successfully with command: {' '.join(cmd)}")
            return True
        except Exception as e:
            LOGGER.error(f"Exception occurred while applying patch with command: {' '.join(cmd)}")
            raise e

    def run_test_with_testScript(self, tc_script: str):
        tc_dir = os.path.dirname(tc_script)
        tc_name = os.path.basename(tc_script)
        res = sp.run(
            f"./{tc_name}",
            shell=True, cwd=tc_dir,
            stderr=sp.DEVNULL, stdout=sp.DEVNULL,
            env=os.environ
        )
        if res.returncode == 0:
            LOGGER.info(f"Test case {tc_name} passed")
        elif res.returncode == 1:
            LOGGER.info(f"Test case {tc_name} failed")
        else:
            LOGGER.info(f"Test case {tc_name} crashed with return code {res.returncode}")
        return res.returncode

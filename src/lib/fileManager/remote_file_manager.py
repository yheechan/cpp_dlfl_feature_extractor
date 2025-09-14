import logging

from lib.fileManager.file_manager import FileManager
from utils.file_utils import *
from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class RemoteFileManager(FileManager):
    def __init__(self):
        LOGGER.info("RemoteFileManager initialized")

    def make_specific_directory(self, dir_path: str, machine: str = None):
        cmd = [
            "ssh", machine,
            "mkdir", "-p", dir_path
        ]
        execute_command_as_list(cmd)
        LOGGER.debug(f"Remote directory created at: {dir_path}")
    
    def remove_specific_directory(self, dir_path, machine = None):
        cmd = [
            "ssh", machine,
            "rm", "-rf", dir_path
        ]
        execute_command_as_list(cmd)
        LOGGER.debug(f"Remote directory removed at: {dir_path}")

    def copy_specific_directory(self, src: str, dest: str, machine: str = None):
        cmd = [
            "rsync", "-t", "-r", 
            f"{src}", f"{machine}:{dest}"
        ]
        execute_command_as_list(cmd)
        LOGGER.debug(f"Remote directory copied from {src} to {dest}")
    
    def copy_specific_file(self, src: str, dest: str, machine: str = None):
        cmd = [
            "rsync", "-t", 
            f"{src}", f"{machine}:{dest}"
        ]
        execute_command_as_list(cmd)
        LOGGER.debug(f"Remote file copied from {src} to {dest}")

    def remove_specific_file(self, file_path: str, machine: str = None):
        cmd = [
            "ssh", machine,
            "rm", "-f", file_path
        ]
        execute_command_as_list(cmd)
        LOGGER.debug(f"Remote file removed at: {file_path}")

    def zip_specific_directory(self, src: str, zip_path: str, machine: str = None):
        cmd = [
            "ssh", machine,
            "zip", "-r", f"{zip_path}.zip", src,
            "&&", "rm", "-rf", src
        ]
        execute_command_as_list(cmd)
        LOGGER.debug(f"Remote directory zipped from {src} to {zip_path}.zip")

    def unzip_specific_directory(self, zip_path: str, extract_to: str, machine: str = None):
        cmd = [
            "ssh", machine,
            "unzip", "-o", f"{zip_path}.zip", "-d", extract_to
        ]
        execute_command_as_list(cmd)
        LOGGER.debug(f"Remote zip file {zip_path} extracted to {extract_to}")

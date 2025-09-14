import logging

from lib.fileManager.file_manager import FileManager
from utils.file_utils import *

LOGGER = logging.getLogger(__name__)

class LocalFileManager(FileManager):
    def __init__(self):
        LOGGER.info("LocalFileManager initialized")

    def make_specific_directory(self, dir_path: str, machine: str = None):
        make_directory(dir_path)
        LOGGER.debug(f"Local directory created at: {dir_path}")
    
    def remove_specific_directory(self, dir_path, machine: str = None):
        remove_directory(dir_path)
        LOGGER.debug(f"Local directory removed at: {dir_path}")

    def copy_specific_directory(self, src: str, dest: str, machine: str = None):
        copy_directory(src, dest)
        LOGGER.debug(f"Local directory copied from {src} to {dest}")

    def copy_specific_file(self, src: str, dest: str, machine: str = None):
        copy_file(src, dest)
        LOGGER.debug(f"Local file copied from {src} to {dest}")

    def remove_specific_file(self, file_path: str, machine: str = None):
        remove_file(file_path)
        LOGGER.debug(f"Local file removed at: {file_path}")
    
    def zip_specific_directory(self, src: str, zip_path: str, machine: str = None):
        zip_directory(src, zip_path)
        LOGGER.debug(f"Local directory zipped from {src} to {zip_path}.zip")

    def unzip_specific_directory(self, zip_path: str, extract_to: str, machine: str = None):
        unzip_directory(zip_path, extract_to)
        LOGGER.debug(f"Local zip file {zip_path} extracted to {extract_to}")

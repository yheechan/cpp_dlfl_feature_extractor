from abc import ABC, abstractmethod

from lib.subject import Subject
from lib.experiment_configs import ExperimentConfigs
from utils.file_utils import *

class FileManager(ABC):
    """Abstract base class for file managers"""

    def make_directory(self, dir_path: str):
        make_directory(dir_path)

    def remove_directory(self, dir_path: str):
        remove_directory(dir_path)
    
    def copy_directory(self, src: str, dest: str):
        copy_directory(src, dest)
    
    def copy_file(self, src: str, dest: str):
        copy_file(src, dest)
    
    def remove_file(self, file_path: str):
        remove_file(file_path)

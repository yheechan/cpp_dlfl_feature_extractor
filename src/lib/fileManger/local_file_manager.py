import logging

from lib.fileManger.file_manager import FileManager
from utils.file_utils import *

LOGGER = logging.getLogger(__name__)

class LocalFileManager(FileManager):
    def __init__(self):
        LOGGER.info("LocalFileManager initialized")
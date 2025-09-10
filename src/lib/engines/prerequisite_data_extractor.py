import logging
import os
from pathlib import Path
import random

from lib.engines.engine import Engine
from lib.experiment_configs import ExperimentConfigs

from utils.command_utils import *

LOGGER = logging.getLogger(__name__)

class PrerequisiteDataTester(Engine):
    def __init__(self, CONFIG: ExperimentConfigs):
        super().__init__(CONFIG)
        LOGGER.info("PrerequisiteDataTester initialized")

    def run(self):
        """Run the prerequisite data testing process"""
        LOGGER.info("Running Prerequisite Data Tester")

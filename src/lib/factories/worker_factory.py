import logging
from typing import Dict, Type

from lib.experiment_configs import ExperimentConfigs
from lib.workers.worker import Worker
from lib.workers.mutant_bug_tester import MutantBugTester
from lib.workers.usable_bug_tester import UsableBugTester
from lib.workers.prerequisite_data_tester import PrerequisiteDataTester

LOGGER = logging.getLogger(__name__)


class WorkerFactory:
    """Factory class for creating different types of workers"""
    
    # Registry of available workers
    _workers: Dict[str, Type[Worker]] = {
        "mutant_bug_tester": MutantBugTester,
        "usable_bug_tester": UsableBugTester,
        "prerequisite_data_tester": PrerequisiteDataTester,
        # Add more workers here as you implement them
        # "code_reviewer": CodeReviewer,
        # "test_runner": TestRunner,
    }
    
    @classmethod
    def create_worker(cls, CONFIG: ExperimentConfigs) -> Worker:
        """Create and return a worker instance based on the specified type"""
        if CONFIG.ARGS.worker_type not in cls._workers:
            available_types = ", ".join(cls._workers.keys())
            error_msg = f"Unknown worker type: {CONFIG.ARGS.worker_type}. Available types: {available_types}"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        worker_class = cls._workers[CONFIG.ARGS.worker_type]
        worker_instance = worker_class(CONFIG)
        LOGGER.info(f"Created worker of type: {CONFIG.ARGS.worker_type}")
        return worker_instance
    
    @classmethod
    def get_available_workers(cls) -> list:
        """Return a list of available worker types"""
        return list(cls._workers.keys())
    
    @classmethod
    def register_worker(cls, worker_type: str, worker_class_path: str):
        """Register a new worker type (useful for plugins or extensions)"""
        cls._workers[worker_type] = worker_class_path
        LOGGER.info(f"Registered new worker type: {worker_type}")
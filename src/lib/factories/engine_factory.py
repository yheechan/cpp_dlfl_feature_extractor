import logging
from typing import Dict, Type

from lib.experiment_configs import ExperimentConfigs

from lib.engines.engine import Engine
from lib.engines.mutant_bug_generator import MutantBugGenerator
from lib.engines.usable_bug_selector import UsableBugSelector
from lib.engines.prerequisite_data_extractor import PrerequisiteDataExtractor
from lib.engines.mutant_mutant_generator import MutantMutantGenerator
from lib.engines.mutation_testing_result_extractor import MutationTestingResultExtractor

from lib.engines.dataset_constructor import DatasetConstructor
from lib.engines.dataset_postprocessor import DatasetPostprocessor

LOGGER = logging.getLogger(__name__)


class EngineFactory:
    """Factory class for creating different types of engines"""
    
    # Registry of available engines
    _engines: Dict[str, Type[Engine]] = {
        "mutant_bug_generator": MutantBugGenerator,
        "usable_bug_selector": UsableBugSelector,
        "prerequisite_data_extractor": PrerequisiteDataExtractor,
        "mutant_mutant_generator": MutantMutantGenerator,
        "mutation_testing_result_extractor": MutationTestingResultExtractor,
        "dataset_constructor": DatasetConstructor,
        "dataset_postprocessor": DatasetPostprocessor,
    }
    
    @classmethod
    def create_engine(cls, CONFIG: ExperimentConfigs) -> Engine:
        """Create and return an engine instance based on the specified type"""

        if CONFIG.ARGS.engine_type not in cls._engines:
            available_types = ", ".join(cls._engines.keys())
            error_msg = f"Unknown engine type: {CONFIG.ARGS.engine_type}. Available types: {available_types}"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        engine_class = cls._engines[CONFIG.ARGS.engine_type]
        engine_instance = engine_class(CONFIG)
        LOGGER.info(f"Created engine of type: {CONFIG.ARGS.engine_type}")
        return engine_instance
    
    @classmethod
    def get_available_engines(cls) -> list:
        """Return a list of available engine types"""
        return list(cls._engines.keys())
    
    @classmethod
    def register_engine(cls, engine_type: str, engine_class: Type[Engine]):
        """Register a new engine type (useful for plugins or extensions)"""
        cls._engines[engine_type] = engine_class
        LOGGER.info(f"Registered new engine type: {engine_type}")

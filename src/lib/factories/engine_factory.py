import logging
from typing import Dict, Type
from lib.engines.engine import Engine
from lib.engines.mutant_bug_generator import MutantBugGenerator

LOGGER = logging.getLogger(__name__)


class EngineFactory:
    """Factory class for creating different types of engines"""
    
    # Registry of available engines
    _engines: Dict[str, Type[Engine]] = {
        "mutant_bug_generator": MutantBugGenerator,
        # Add more engines here as you implement them
        # "feature_extractor": FeatureExtractor,
        # "code_analyzer": CodeAnalyzer,
    }
    
    def __init__(self, engine_type: str):
        self.engine_type = engine_type
    
    def create_engine(self) -> Engine:
        """Create and return an engine instance based on the specified type"""
        if self.engine_type not in self._engines:
            available_types = ", ".join(self._engines.keys())
            error_msg = f"Unknown engine type: {self.engine_type}. Available types: {available_types}"
            LOGGER.error(error_msg)
            raise ValueError(error_msg)
        
        engine_class = self._engines[self.engine_type]
        engine_instance = engine_class()
        LOGGER.info(f"Created engine of type: {self.engine_type}")
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
        
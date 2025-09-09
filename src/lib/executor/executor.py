from abc import ABC, abstractmethod
import logging

from lib.engine_context import EngineContext

LOGGER = logging.getLogger(__name__)

class Executor(ABC):
    """Abstract base class for executors"""

    def __init__(self):
        LOGGER.info(f"{self.__class__.__name__} initialized")

    @abstractmethod
    def prepare_for_execution(self, CONTEXT: EngineContext):
        """Prepare the execution environment"""
        raise NotImplementedError("Subclasses must implement prepare_for_execution() method")

    @abstractmethod
    def test_for_mutant_bugs(self, CONTEXT: EngineContext, mutant_list: list):
        """Test for mutant bugs"""
        raise NotImplementedError("Subclasses must implement test_for_mutant_bugs() method")
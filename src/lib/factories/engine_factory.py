from lib.engines.mutant_bug_generator import MutantBugGenerator


class EngineFactory:
    def __init__(self, engine_type: str):
        self.engine_type = engine_type
    
    def create_engine(self):
        if self.engine_type == "mutant_bug_generator":
            return MutantBugGenerator()
        else:
            raise ValueError(f"Unknown engine type: {self.engine_type}")
        
from dataclasses import dataclass
from typing import Any

@dataclass
class WorkerContext:
    """Contains all the data needed by executors without circular dependencies"""
    CONFIG: Any  # ExperimentConfigs
    FILE_MANAGER: Any
    SUBJECT: Any
    
    # Directory paths
    tools_dir: str
    log_dir: str
    out_dir: str
    working_dir: str
    working_env_dir: str
    subject_repo: str
    testcases_dir: str
    coverage_dir: str
    line2function_dir: str
    mutant_mutants_dir: str
    
    # Executables
    musicup_exec: str
    extractor_exec: str

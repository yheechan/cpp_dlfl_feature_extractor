from dataclasses import dataclass
from typing import Any

@dataclass
class EngineContext:
    """Contains all the data needed by executors without circular dependencies"""
    CONFIG: Any  # ExperimentConfigs
    FILE_MANAGER: Any
    
    # Directory paths
    tools_dir: str
    log_dir: str
    out_dir: str
    working_dir: str
    working_env_dir: str
    dest_repo: str
    
    # Executables
    musicup_exec: str
    extractor_exec: str

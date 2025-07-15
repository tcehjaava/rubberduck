from enum import Enum
from pathlib import Path
from typing import Any, Dict, TypedDict

from rubberduck.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)


class SWEBenchWorkflowState(TypedDict):
    instance: SWEBenchVerifiedInstance
    current_attempt: int
    max_attempts: int
    result: Any
    error_message: str
    log_dir: Path
    memory: Dict[str, Any]


class SWEBenchWorkflowNode(Enum):
    INIT = "init"
    EXECUTOR = "executor"
    LEADER = "leader"
    LEADER_SHOULD_CONTINUE = "leader_should_continue"
    LOGGER = "logger"
    SETUP = "setup"
    CLEANUP = "cleanup"
    SEMANTIC_PROCESSOR = "semantic_processor"


class SWEBenchWorkflowConfig(TypedDict):
    instance_id: str

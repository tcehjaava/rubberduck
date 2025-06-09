from enum import Enum
from typing import Any, Dict, TypedDict

from rubberduck.autogen.leader_executor.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)


class SWEBenchWorkflowState(TypedDict):
    instance: SWEBenchVerifiedInstance
    current_attempt: int
    max_attempts: int
    result: Any
    error_message: str
    memory: Dict[str, Any]


class SWEBenchWorkflowNode(Enum):
    INIT = "init"
    EXECUTOR = "executor"
    LEADER = "leader"
    REPO_CLONE = "repo_clone"
    SETUP = "setup"
    CLEANUP = "cleanup"


class SWEBenchWorkflowConfig(TypedDict):
    instance_id: str

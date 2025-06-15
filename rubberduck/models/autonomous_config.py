from dataclasses import dataclass
from typing import Any, Dict, Optional

from docker.models.containers import Container


@dataclass
class AutonomousAgentConfig:
    assistant_name: str
    proxy_name: str
    system_message: str
    model_config: str = "gpt-4.1-2025-04-14"
    termination_marker: str = "TERMINATE"
    max_turns: int = 100
    code_execution_config: Optional[Dict[str, Any]] = None
    docker_runner: Optional[Container] = None
    retry_attempts: int = 3
    retry_wait_multiplier: int = 10

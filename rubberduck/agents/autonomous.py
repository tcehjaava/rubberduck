from functools import partial
from typing import Optional

from autogen import AssistantAgent, UserProxyAgent
from tenacity import retry, stop_after_attempt, wait_exponential

from rubberduck.autogen.leader_executor.config import load_llm_config
from rubberduck.autogen.leader_executor.models.autonomous_config import (
    AutonomousAgentConfig,
)
from rubberduck.autogen.leader_executor.utils.helpers import is_termination_msg


class AutonomousAgent:
    def __init__(self, config: AutonomousAgentConfig):
        self.config = config
        self._setup_agents()

    def _setup_agents(self):
        config_list = load_llm_config(self.config.model_config)

        termination_check = partial(is_termination_msg, termination_marker=self.config.termination_marker)

        self.assistant = AssistantAgent(
            name=self.config.assistant_name,
            system_message=self.config.system_message,
            llm_config={"config_list": config_list, "temperature": self.config.temperature},
            is_termination_msg=None,
            human_input_mode="NEVER",
        )

        proxy_kwargs = {
            "name": self.config.proxy_name,
            "human_input_mode": "NEVER",
            "is_termination_msg": termination_check,
            "llm_config": False,
        }

        if self.config.code_execution_config:
            proxy_kwargs["code_execution_config"] = self.config.code_execution_config
        else:
            proxy_kwargs["code_execution_config"] = False

        self.proxy = UserProxyAgent(**proxy_kwargs)

    def execute_task(self, task: str, custom_max_turns: Optional[int] = None):
        max_turns = custom_max_turns or self.config.max_turns

        retry_decorator = retry(
            stop=stop_after_attempt(self.config.retry_attempts),
            wait=wait_exponential(multiplier=self.config.retry_wait_multiplier),
            reraise=True,
        )

        @retry_decorator
        def _execute():
            return self.proxy.initiate_chat(recipient=self.assistant, message=task, max_turns=max_turns)

        return _execute()

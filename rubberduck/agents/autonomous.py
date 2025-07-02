from functools import partial
from typing import Optional

import timeout_decorator
from autogen import AssistantAgent, UserProxyAgent
from tenacity import retry, stop_after_attempt, wait_exponential

from rubberduck.config import load_llm_config
from rubberduck.models.autonomous_config import (
    AutonomousAgentConfig,
)
from rubberduck.tools.apply_patch import (
    create_patch_reply,
    prepend_patch_status,
)
from rubberduck.tools.execution_reply import create_execution_reply
from rubberduck.utils.message_helpers import (
    clean_message_content,
    is_termination_msg,
)


class AutonomousAgent:
    def __init__(self, config: AutonomousAgentConfig):
        self.config = config
        self._setup_agents()

    def _setup_agents(self):
        self.assistant = AssistantAgent(
            name=self.config.assistant_name,
            system_message=self.config.system_message,
            llm_config=load_llm_config(self.config.model_config),
            is_termination_msg=None,
            human_input_mode="NEVER",
        )

        proxy_kwargs = {
            "name": self.config.proxy_name,
            "human_input_mode": "NEVER",
            "is_termination_msg": partial(is_termination_msg, termination_marker=self.config.termination_marker),
            "llm_config": False,
            "code_execution_config": False,
        }

        self.proxy = UserProxyAgent(**proxy_kwargs)

        if self.config.docker_runner:
            self.proxy.register_reply(
                trigger=self.assistant,
                reply_func=create_patch_reply(self.config.docker_runner),
                position=0,
            )

            self.proxy.register_reply(
                trigger=self.assistant,
                reply_func=create_execution_reply(
                    self.config.docker_runner, semantic_search=self.config.semantic_search
                ),
                position=1,
            )

            self.proxy.register_hook("process_message_before_send", prepend_patch_status)

        self.proxy.register_hook(hookable_method="process_last_received_message", hook=clean_message_content)

    def execute_task(self, task: str, custom_max_turns: Optional[int] = None):
        max_turns = custom_max_turns or self.config.max_turns

        @retry(
            stop=stop_after_attempt(self.config.retry_attempts),
            wait=wait_exponential(multiplier=self.config.retry_wait_multiplier),
            reraise=True,
        )
        @timeout_decorator.timeout(180)
        def _execute():
            attempt = _execute.retry.statistics.get("attempt_number", 1)
            return self.proxy.initiate_chat(
                recipient=self.assistant,
                message=task if attempt == 1 else None,
                clear_history=(attempt == 1),
                max_turns=max_turns,
            )

        return _execute()

from functools import partial
from typing import Optional

from autogen import AssistantAgent, ChatResult, UserProxyAgent
from loguru import logger

from rubberduck.config import load_llm_config
from rubberduck.models.autonomous_config import (
    AutonomousAgentConfig,
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
                reply_func=create_execution_reply(
                    self.config.docker_runner, semantic_search=self.config.semantic_search
                ),
                position=0,
            )

        self.proxy.register_hook(hookable_method="process_last_received_message", hook=clean_message_content)

    def execute_task(self, task: str, custom_max_turns: Optional[int] = None):
        max_turns = custom_max_turns or self.config.max_turns

        def _execute():
            try:
                return self.proxy.initiate_chat(
                    recipient=self.assistant,
                    message=task,
                    clear_history=True,
                    max_turns=max_turns,
                )
            except Exception as e:
                chat_history = self.proxy.chat_messages.get(self.assistant, []).copy()

                message_count = len(chat_history)

                chat_history.append(
                    {
                        "role": "system",
                        "content": f"[ERROR] Execution stopped: {type(e).__name__}: {str(e)}",
                        "name": "system",
                    }
                )

                chat_result = ChatResult(
                    chat_history=chat_history,
                    summary=f"Execution stopped after {message_count} messages: {type(e).__name__}",
                    human_input=self.proxy._human_input,
                )

                logger.warning(f"Error occurred after {message_count} messages: {e}", exc_info=True)

                return chat_result

        return _execute()

from functools import partial

from autogen import AssistantAgent, UserProxyAgent
from loguru import logger

from rubberduck.autogen.leader_executor.config import load_llm_config
from rubberduck.autogen.leader_executor.models import SWEBenchVerifiedInstance
from rubberduck.autogen.leader_executor.prompts import load_markdown_message
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor
from rubberduck.autogen.leader_executor.utils.helpers import is_termination_msg


class ExecutorAgent:
    def __init__(
        self,
        repo_executor: RepoDockerExecutor,
        instance: SWEBenchVerifiedInstance,
        model_config: str = "default_executor",
    ):
        self._repo_executor: RepoDockerExecutor = repo_executor
        config_list = load_llm_config(model_config)

        termination_check = partial(is_termination_msg, termination_marker="TERMINATE")

        self.executor = AssistantAgent(
            name="EXECUTOR",
            system_message=load_markdown_message("executor_system_message.md", repo_name=instance.repo_subdir_name),
            llm_config={"config_list": config_list, "temperature": 0},
            is_termination_msg=termination_check,
            human_input_mode="NEVER",
        )

        self.proxy = UserProxyAgent(
            name="EXECUTOR_PROXY",
            human_input_mode="NEVER",
            code_execution_config={
                "executor": self._repo_executor,
            },
            llm_config=False,
            is_termination_msg=termination_check,
        )

    def perform_task(self, task: str) -> None:
        logger.info("ExecutorAgent received task: %s", task)
        chat_result = self.proxy.initiate_chat(self.executor, message=task, max_turns=25)
        return chat_result.summary if hasattr(chat_result, "summary") else "Task executed, No summary to return."

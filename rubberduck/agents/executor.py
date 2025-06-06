import traceback
from functools import partial

from autogen import AssistantAgent, ChatResult, UserProxyAgent
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
            system_message=load_markdown_message("executor.md", repo_name=instance.repo_subdir_name),
            llm_config={"config_list": config_list, "temperature": 0},
            is_termination_msg=None,
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

    def perform_task(self, task: str):
        logger.info("ExecutorAgent started a task...")
        try:
            chat_result = self.proxy.initiate_chat(self.executor, message=task, max_turns=1)
            return chat_result
        except Exception as e:
            logger.error(f"ExecutorAgent encountered an exception: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            error_message = f"EXECUTION FAILED: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"

            error_chat_result = ChatResult(
                chat_id=None,
                summary=f"Task failed due to exception: {str(e)}",
                chat_history=[
                    {"role": "user", "name": "EXECUTOR_PROXY", "content": task},
                    {"role": "assistant", "name": "EXECUTOR", "content": error_message},
                ],
                cost=None,
                human_input=None,
            )

            return error_chat_result

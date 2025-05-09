import logging

from autogen import AssistantAgent, UserProxyAgent

from rubberduck.autogen.leader_executor.config import load_llm_config
from rubberduck.autogen.leader_executor.models import SWEBenchVerifiedInstance
from rubberduck.autogen.leader_executor.prompts import load_markdown_message
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor

logger = logging.getLogger(__name__)


def is_termination_msg(msg: dict) -> bool:
    return msg.get("content", "").rstrip().endswith("TERMINATE")


class ExecutorAgent:
    def __init__(
        self,
        repo_executor: RepoDockerExecutor,
        instance: SWEBenchVerifiedInstance,
        model_config: str = "default_executor",
    ):
        self._repo_executor: RepoDockerExecutor = repo_executor
        config_list = load_llm_config(model_config)

        self.executor = AssistantAgent(
            name="EXECUTOR",
            system_message=load_markdown_message("executor_system_message.md", repo_name=instance.repo_subdir_name),
            description=load_markdown_message("executor_description.md"),
            llm_config={"config_list": config_list, "temperature": 0},
            is_termination_msg=is_termination_msg,
            human_input_mode="NEVER",
        )

        self.proxy = UserProxyAgent(
            name="DRIVER",
            human_input_mode="NEVER",
            code_execution_config={
                "executor": self._repo_executor,
            },
            llm_config=False,
            is_termination_msg=is_termination_msg,
        )

    def perform_task(self, task: str) -> None:
        logger.info("ExecutorAgent received task: %s", task)
        self.proxy.initiate_chat(self.executor, message=task)

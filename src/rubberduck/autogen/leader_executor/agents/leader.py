from functools import partial

from autogen import AssistantAgent, UserProxyAgent, register_function
from loguru import logger

from rubberduck.autogen.leader_executor.agents.executor import ExecutorAgent
from rubberduck.autogen.leader_executor.config import load_llm_config
from rubberduck.autogen.leader_executor.models import SWEBenchVerifiedInstance
from rubberduck.autogen.leader_executor.prompts import load_markdown_message
from rubberduck.autogen.leader_executor.utils.helpers import is_termination_msg


class LeaderAgent:
    def __init__(
        self,
        executor_agent: ExecutorAgent,
        instance: SWEBenchVerifiedInstance,
        model_config: str = "default_leader",
    ):
        self.executor_agent = executor_agent
        self.instance = instance
        config_list = load_llm_config(model_config)

        system_message = load_markdown_message(
            "leader_system_message.md", repo_name=instance.repo_subdir_name, commit_hash=instance.base_commit
        )
        termination_check = partial(is_termination_msg, termination_marker="TERMINATE")

        self.leader = AssistantAgent(
            name="LEADER",
            system_message=system_message,
            llm_config={"config_list": config_list, "temperature": 0},
            is_termination_msg=termination_check,
            human_input_mode="NEVER",
        )

        self.leader_proxy = UserProxyAgent(
            name="LEADER_PROXY",
            human_input_mode="NEVER",
            is_termination_msg=termination_check,
            llm_config=False,
        )

        def perform_task_wrapper(task: str) -> None:
            return self.executor_agent.perform_task(task)

        register_function(
            perform_task_wrapper,
            caller=self.leader,
            executor=self.leader_proxy,
            name="perform_task",
            description="Delegate task execution to ExecutorAgent in a containerized environment.",
        )

    def solve_issue(self, problem_statement: str) -> str:
        formatted_issue = (
            f"Please solve the following software engineering issue for {self.instance.repo_subdir_name}:\n\n"
            f"{problem_statement}\n\n"
            f"Remember to follow the ReAct protocol - think through your solution, "
            f"take actions by delegating tasks, and observe results."
        )

        logger.info(f"LeaderAgent solving issue for {self.instance.repo_subdir_name}")
        chat_result = self.leader_proxy.initiate_chat(recipient=self.leader, message=formatted_issue, max_turns=25)

        return chat_result.summary if hasattr(chat_result, "summary") else "Issue solved, no summary available."

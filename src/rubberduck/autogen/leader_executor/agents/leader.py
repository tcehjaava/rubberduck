import json
from functools import partial

from autogen import AssistantAgent, UserProxyAgent
from loguru import logger

from rubberduck.autogen.leader_executor.agents.executor import ExecutorAgent
from rubberduck.autogen.leader_executor.config import load_llm_config
from rubberduck.autogen.leader_executor.models import SWEBenchVerifiedInstance
from rubberduck.autogen.leader_executor.models.leader import (
    LeaderReviewResponse,
)
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
            "leader.md",
            response_schema=json.dumps(LeaderReviewResponse.model_json_schema(), indent=2),
        )
        termination_check = partial(is_termination_msg, termination_marker="TERMINATE")

        self.leader = AssistantAgent(
            name="LEADER",
            system_message=system_message,
            llm_config={"config_list": config_list, "temperature": 1},
            is_termination_msg=termination_check,
            human_input_mode="NEVER",
        )

        self.leader_proxy = UserProxyAgent(
            name="LEADER_PROXY",
            human_input_mode="NEVER",
            is_termination_msg=termination_check,
            llm_config=False,
        )

    def solve_issue(self, problem_statement: str) -> str:
        logger.info(f"LeaderAgent solving issue for {self.instance.repo_subdir_name}")
        chat_result = self.leader_proxy.initiate_chat(recipient=self.leader, message=problem_statement, max_turns=25)
        return chat_result

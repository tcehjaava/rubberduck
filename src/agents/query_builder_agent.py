# src/agents/query_builder_agent.py

from typing import Optional

from agents import BaseAgent
from config import AgentConfig
from models import (
    AgentExecutionContext,
    IssueData,
    NextStep,
    WorkflowState,
)

query_builder_agent_config = AgentConfig(
    SYSTEM_PROMPT=None,
    TEMPERATURE=0.0,
)


class QueryBuilderAgent(BaseAgent):
    def run(self, state: WorkflowState) -> dict:
        raise NotImplementedError("Subclasses must implement run method.")

    def on_retry(self, context: AgentExecutionContext[IssueData]) -> None:
        raise NotImplementedError("Subclasses must implement on_retry method.")

    def on_max_retries_exceeded(self, context: AgentExecutionContext[IssueData]) -> None:
        raise NotImplementedError("Subclasses must implement on_max_retries_exceeded method.")

    def validate(self, result: IssueData) -> Optional[str]:
        raise NotImplementedError("Subclasses must implement validate method.")

    def next_step(self, state: WorkflowState) -> NextStep:
        raise NotImplementedError("Implement the workflow next step decision logic")

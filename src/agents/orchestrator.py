# src/agents/orchestrator.py

import json
import logging
from typing import Optional

from agents import BaseAgent, IssueDataExtractorAgent
from config import AgentConfig
from models import (
    AgentExecutionContext,
    MessageRole,
    NextStep,
    OrchestratorAction,
    OrchestratorOutput,
    WorkflowState,
)

SYSTEM_PROMPT_TEMPLATE = """
You are an Orchestrator Agent responsible for determining the next steps in a debugging workflow.

CURRENT ISSUE DATA:
{issue_data_json}

GOALS:
1. Identify the optimal next action based on the issue data.
2. Clearly define tasks for downstream agents.
3. Decide when further analysis is no longer necessary.

AVAILABLE ACTIONS:
- RELEVANCE_SEARCH: Initiate code search to find relevant files and code segments.
- END: Terminate the workflow when further analysis is not possible or necessary.

Output must be strictly JSON format without extra commentary.
"""

RETRY_PROMPT_TEMPLATE = """
Previous attempt resulted in error: {error}. Please revise your response.
"""

USER_PROMPT_TEMPLATE = """
Determine the next action and associated task.
"""

orchestrator_config = AgentConfig(
    SYSTEM_PROMPT=SYSTEM_PROMPT_TEMPLATE,
    TEMPERATURE=0.3,
)


class Orchestrator(BaseAgent[OrchestratorOutput]):

    def run(self, state: WorkflowState) -> dict:
        issue_data_context = state.get_latest_context(IssueDataExtractorAgent.__name__)

        issue_data_record = issue_data_context.get_last_record()
        assert issue_data_record.raw_result, "Orchestrator called without issue_data_record."

        issue_data_json = json.dumps(issue_data_record.raw_result, indent=2)

        orchestrator_context = self.create_context(state)
        orchestrator_context.set_extra_template_vars({"issue_data_json": issue_data_json})

        messages = orchestrator_context.build_conversation_messages()
        messages.append((MessageRole.USER, USER_PROMPT_TEMPLATE))

        self.execute(messages, orchestrator_context)
        return state.build_context_update(self.agent_name, orchestrator_context)

    def validate(self, result: OrchestratorOutput) -> Optional[str]:
        errors = []

        if result.action == OrchestratorAction.RELEVANCE_SEARCH and not result.task:
            errors.append("RELEVANCE_SEARCH requires a defined task.")

        if not result.conversation_summary:
            errors.append("A conversation summary must be provided.")

        if errors:
            return "; ".join(errors)

        return None

    def on_retry(self, context: AgentExecutionContext[OrchestratorOutput]) -> None:
        last_record = context.get_last_record()
        assert last_record.error, "on_retry called without an error in last record."

        messages = context.build_conversation_messages(use_full_history=True)
        messages.append((MessageRole.USER, RETRY_PROMPT_TEMPLATE))

        context.set_extra_template_vars(
            {
                **context.get_extra_template_vars(),
                "error": last_record.error,
            }
        )

        self.execute(messages, context)

    def on_max_retries_exceeded(self, context: AgentExecutionContext[OrchestratorOutput]) -> None:
        pass

    def next_step(self, state: WorkflowState) -> NextStep:
        context = state.get_latest_context(self.agent_name)
        last_record = context.get_last_record()

        if not last_record or last_record.error:
            error_details = last_record.error if last_record else "No execution record found"
            logging.error(f"Orchestrator failed: {error_details}.")
            return NextStep.END

        return NextStep.END if last_record.result.action == OrchestratorAction.END else NextStep.NEXT

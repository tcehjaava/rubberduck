# src/agents/file_prioritization_agent.py

import logging
from typing import Optional

from rubberduck.langgraph.graph_orchestrator.agents.base_agent import BaseAgent
from rubberduck.langgraph.graph_orchestrator.agents.issue_data_extractor import (
    IssueDataExtractorAgent,
)
from rubberduck.langgraph.graph_orchestrator.agents.query_builder import (
    QueryBuilderAgent,
)
from rubberduck.langgraph.graph_orchestrator.config import AgentConfig
from rubberduck.langgraph.graph_orchestrator.models import (
    AgentExecutionContext,
    FilePrioritizationOutput,
    MessageRole,
    NextStep,
    SearchQuery,
    WorkflowState,
)
from rubberduck.langgraph.graph_orchestrator.tools.sourcegraph import SourcegraphClient

SYSTEM_PROMPT = """
You are a File Prioritization Agent responsible for evaluating files by their relevance to the issue being investigated.

YOUR TASK:
Analyze search results and determine how relevant each file is to the issue described. For each file, you must:
1. Assign a relevance level
2. Provide clear reasoning for your evaluation

RELEVANCE LEVELS:
- RELEVANT: Files that are related to the issue and may need modification or provide useful context
- NOT_RELEVANT: Files that are not related to the issue
- NOT_SURE: Files where relevance couldn't be determined with confidence

ISSUE INFORMATION:
{issue_data}

SEARCH QUERY USED:
{search_query}

SEARCH RESULTS:
{search_results}
"""


USER_PROMPT_TEMPLATE = """
Review the search results and evaluate each file's relevance to the issue. For each file, provide:

1. A relevance level (RELEVANT, NOT_RELEVANT, or NOT_SURE)
2. Clear reasoning explaining why you assigned that relevance level

Focus on understanding how each file relates to the described issue.
"""

RETRY_PROMPT_TEMPLATE = """
Previous attempt resulted in error: {error}. Please revise your response.
"""

file_prioritization_config = AgentConfig(
    SYSTEM_PROMPT=SYSTEM_PROMPT,
    TEMPERATURE=0.4,
    # MODEL_NAME="claude-3-7-sonnet-20250219",
)


class FilePrioritizationAgent(BaseAgent[FilePrioritizationOutput]):
    def __init__(self, config: AgentConfig):
        super().__init__(config)

    def run(self, state: WorkflowState) -> dict:
        query_builder_context = state.get_latest_context(QueryBuilderAgent.__name__)
        query_builder_record = query_builder_context.get_last_successful_record()

        assert (
            query_builder_record and query_builder_record.result
        ), "FilePrioritizationAgent called without query_builder_record."

        search_query: SearchQuery = query_builder_record.result

        issue_data_context = state.get_latest_context(IssueDataExtractorAgent.__name__)
        issue_data_record = issue_data_context.get_last_record()
        issue_data = issue_data_record.raw_result

        search_results = SourcegraphClient.search_relevance_files(search_query.query)
        search_results_json = search_results.model_dump_json(indent=2)

        prioritization_context = self.create_context(state)
        prioritization_context.set_extra_template_vars(
            {
                "issue_data": issue_data,
                "search_query": search_query.model_dump_json(indent=2),
                "search_results": search_results_json,
            }
        )

        messages = prioritization_context.build_conversation_messages()
        messages.append((MessageRole.USER, USER_PROMPT_TEMPLATE))

        self.execute(messages, prioritization_context)
        return state.build_context_update(self.agent_name, prioritization_context)

    def validate(
        self, context: AgentExecutionContext[FilePrioritizationOutput], result: FilePrioritizationOutput
    ) -> Optional[str]:
        return None

    def on_retry(self, context: AgentExecutionContext[FilePrioritizationOutput]) -> None:
        last_record = context.get_last_record()
        assert last_record.error, "on_retry called without an error in last record."

        messages = context.build_conversation_messages()
        messages.append((MessageRole.USER, RETRY_PROMPT_TEMPLATE.format(error=last_record.error)))

        self.execute(messages, context)

    def on_max_retries_exceeded(self, context: AgentExecutionContext[FilePrioritizationOutput]) -> None:
        logging.warning("Max retries exceeded for FilePrioritizationAgent. Proceeding with last attempt.")

    def next_step(self, state: WorkflowState) -> NextStep:
        context = state.get_latest_context(self.agent_name)
        last_record = context.get_last_record()

        if not last_record or last_record.error:
            error_details = last_record.error if last_record else "No execution record found"
            logging.error(f"File Prioritization failed: {error_details}.")
            return NextStep.END

        return NextStep.NEXT

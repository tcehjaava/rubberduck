# agents/query_builder_agent.py

import logging
from typing import Optional

from rubberduck.langgraph.graph_orchestrator.agents.base_agent import BaseAgent
from rubberduck.langgraph.graph_orchestrator.agents.issue_data_extractor import (
    IssueDataExtractorAgent,
)
from rubberduck.langgraph.graph_orchestrator.agents.orchestrator import Orchestrator
from rubberduck.langgraph.graph_orchestrator.config import AgentConfig
from rubberduck.langgraph.graph_orchestrator.models import (
    AgentExecutionContext,
    MessageRole,
    NextStep,
    QueryType,
    SearchQuery,
    WorkflowState,
)
from rubberduck.langgraph.graph_orchestrator.models.output_models import IssueData
from rubberduck.langgraph.graph_orchestrator.tools.sourcegraph.sourcegraph_client import (
    SourcegraphClient,
)

SYSTEM_PROMPT = """
You are a Query Builder Agent responsible for creating precise Sourcegraph search queries based on provided data.

SOURCEGRAPH QUERY GUIDELINES:
1. Always include `repo:^github.com/{repo_name}$@{base_commit}`
2. Combine terms explicitly using `AND`/`OR` with parentheses for grouping
3. Avoid ungrouped space-separated terms
4. Only return valid JSON matching the SearchQuery schema; no additional commentary
5. Exclude irrelevant file types by explicitly filtering out common non-relevant extensions
   (e.g., `-file:.*\\.md$`, `-file:.*\\.txt$`) unless specifically needed

ISSUE DATA:
{issue_data}

ORCHESTRATOR TASK:
{orchestrator_task}
"""

USER_PROMPT_TEMPLATE = """
Generate a Sourcegraph search query to locate relevant code for debugging the described issue.
"""

RETRY_PROMPT_TEMPLATE = """
Previous query attempt resulted in error: {error}. Please revise your response.
"""


REFINEMENT_PROMPT_TEMPLATE = """
I've executed your search query and here are the results:

{search_results}

Please review these results and refine as follows:

1. If results are relevant, focused, and of manageable size (under 20 files), return the EXACT SAME query

2. If results are too numerous (20+ files) or contain irrelevant content, provide a refined query that:
   - Narrows scope by targeting specific directories or file types
   - Uses more precise keywords or patterns
   - Excludes irrelevant file types using "-filename:" filters
   - Prioritizes core implementation files over tests/docs when appropriate
   - Uses "path:" or "filename:" qualifiers to target specific areas

3. If results seem incomplete, broaden slightly using OR operators or wildcards

Remember to maintain the required repo pattern and balance between precision and recall - prioritize including ALL
potentially relevant files while excluding clear noise.
"""

query_builder_config = AgentConfig(
    SYSTEM_PROMPT=SYSTEM_PROMPT,
    TEMPERATURE=0.4,
    # MODEL_NAME="claude-3-7-sonnet-20250219",
)


class QueryBuilderAgent(BaseAgent[SearchQuery]):
    def __init__(self, config: AgentConfig):
        super().__init__(config)

    def run(self, state: WorkflowState) -> dict:
        issue_data_context = state.get_latest_context(IssueDataExtractorAgent.__name__)
        orchestrator_context = state.get_latest_context(Orchestrator.__name__)

        issue_data_record = issue_data_context.get_last_record()
        orchestrator_record = orchestrator_context.get_last_record()

        assert issue_data_record and issue_data_record.raw_result, "QueryBuilder called without issue_data_record."
        assert (
            orchestrator_record and orchestrator_record.raw_result
        ), "QueryBuilder called without orchestrator_record."
        assert orchestrator_record.result.task, "Orchestrator did not provide a task."

        issue_data = issue_data_record.raw_result
        issue_data_obj = IssueData.model_validate(issue_data)
        orchestrator_task = orchestrator_record.result.task.model_dump()

        repo_name = issue_data_obj.repo_name
        base_commit = issue_data_obj.base_commit

        assert repo_name, "Repository name is required but was not provided."
        assert base_commit, "Base commit is required but was not provided."

        query_builder_context = self.create_context(state)
        # TODO: Need a better way to set max_retries
        query_builder_context.max_retries = 10

        query_builder_context.set_extra_template_vars(
            {
                "repo_name": repo_name,
                "base_commit": base_commit,
                "orchestrator_task": orchestrator_task,
                "issue_data": issue_data,
            }
        )

        current_query = None
        previous_query = None

        while (
            previous_query is None or previous_query.query != current_query.query
        ) and query_builder_context.has_more_retries():
            previous_query = current_query
            messages = query_builder_context.build_conversation_messages()

            if previous_query is None:
                prompt = USER_PROMPT_TEMPLATE
            else:
                search_results = SourcegraphClient.get_relevance_summary(current_query.query)
                search_results_json = search_results.model_dump_json(indent=2)

                prompt = REFINEMENT_PROMPT_TEMPLATE.format(search_results=search_results_json)

            messages.append((MessageRole.USER, prompt))
            self.execute(messages, query_builder_context)

            last_record = query_builder_context.get_last_record()
            current_query = last_record.result

        logging.info(f"[{self.agent_name}] Query converged after {query_builder_context.attempts-1} iterations.")
        return state.build_context_update(self.agent_name, query_builder_context)

    def validate(self, context: AgentExecutionContext[SearchQuery], result: SearchQuery) -> Optional[str]:
        errors = []

        extra_vars = context.get_extra_template_vars()
        repo_name = extra_vars.get("repo_name")
        base_commit = extra_vars.get("base_commit")

        if result.query_type == QueryType.RELEVANT_FILES:
            expected_repo_pattern = f"repo:^github.com/{repo_name}$@{base_commit}"
            if expected_repo_pattern not in result.query:
                errors.append(f"Query must include '{expected_repo_pattern}'")

            try:
                response = SourcegraphClient.get_relevance_summary(result.query)
                if response.matches == 0 or response.file_count == 0:
                    errors.append(f"Query returned no results. Response: {response}")
            except Exception as e:
                errors.append(f"Error executing query: {str(e)}")

        elif result.query_type == QueryType.FILE_CONTENT:
            expected_prefix = f"repo:^github.com/{repo_name}$@{base_commit} file:"

            if not result.query.startswith(expected_prefix):
                errors.append(f"File content query must start with '{expected_prefix}'")

            file_query_part = result.query[len(expected_prefix) :].strip()
            if " " in file_query_part:
                errors.append(
                    "File content query must specify exactly one file and nothing else."
                    f" Found extra content: '{file_query_part}'"
                )
            try:
                file_content = SourcegraphClient.get_file_content(
                    repo=f"github.com/{repo_name}", commit=base_commit, path=file_query_part
                )

                if not file_content:
                    errors.append(f"File not found or empty content: {file_query_part}")
            except Exception as e:
                errors.append(f"Error fetching file content: {str(e)}")

        if errors:
            return "; ".join(errors)

        return None

    def on_retry(self, context: AgentExecutionContext[SearchQuery]) -> None:
        last_record = context.get_last_record()
        assert last_record.error, "on_retry called without an error in last record."

        messages = context.build_conversation_messages()
        messages.append((MessageRole.USER, RETRY_PROMPT_TEMPLATE.format(error=last_record.error)))

        self.execute(messages, context)

    def on_max_retries_exceeded(self, context: AgentExecutionContext[SearchQuery]) -> None:
        logging.warning("Max retries exceeded for QueryBuilderAgent. Proceeding with last query.")

    def next_step(self, state: WorkflowState) -> NextStep:
        context = state.get_latest_context(self.agent_name)
        last_record = context.get_last_successful_record()

        if not last_record:
            return NextStep.END

        return NextStep.NEXT

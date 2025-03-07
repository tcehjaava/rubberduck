# src/agents/issue_data_extractor.py

import logging
from typing import Optional

from agents import BaseAgent
from config import AgentConfig
from models import IssueData, MessageRole, NextStep, WorkflowState

SYSTEM_PROMPT = """
You are the Structural Foundation Agent in an autonomous code repair system.

Your role is to transform unstructured issue reports into machine-processable data that powers subsequent analysis.

Role in System:
- First critical step in the automated debugging pipeline
- Creates structured representation of the problem for all downstream agents
- Provides search keywords and context for code investigation

Individual Goals:
1. Accurately capture all explicit information from the report
2. Preserve raw context while creating concise summaries
3. Identify technical keywords for code search operations
4. Maintain strict schema compliance for system interoperability

Key Responsibilities:
• Extract verbatim details while preventing information loss
• Discern problem type without external context
• Generate precise search terms from technical content
• Ensure zero hallucination - only explicit input data

Strict Technical Instructions:
1. Return only valid JSON — no Markdown formatting, no code fences, and no extra commentary.
2. Do not wrap the JSON in backticks or any delimiters.
3. Use exactly the fields and structure defined in the provided schema.
4. Set missing fields to null or empty arrays/objects as schema demands.
5. The `problem_type` must be one of: "Bug", "Feature", or "Documentation". Default to "Bug" if unsure.
6. Only use explicitly provided text; do not supplement with external sources.
7. Extract each field faithfully, leaving it null or empty if input lacks data.
8. The `description` is a concise summary; `raw_text` includes all relevant text/logs verbatim.
9. `keywords` should include search terms to locate relevant code files.
10. Output must be strictly JSON format without extra commentary.

Accuracy and schema compliance are critical.
"""

USER_PROMPT_TEMPLATE = """
Here is the input:

Repository: {repo}
Problem Statement: {problem_statement}
Base Commit: {base_commit}

We will use your extracted data to:
• Generate a summary of the issue
• Search for relevant files in the repository using keywords
• Potentially fix the problem

Follow the instructions carefully and rely ONLY on this input for your response.
Do NOT add any details or context that are not directly contained in the input.

Extract the data according to the schema provided to you, and return only valid JSON with no extra commentary.
"""

issue_data_extractor_config = AgentConfig(
    SYSTEM_PROMPT=SYSTEM_PROMPT,
    TEMPERATURE=0.0,  # MODEL_NAME="qwen-max"
)


class IssueDataExtractorAgent(BaseAgent[IssueData]):

    def run(self, state: WorkflowState) -> None:
        raw_inputs = state.raw_inputs
        user_prompt = USER_PROMPT_TEMPLATE.format(**raw_inputs)
        messages = [(MessageRole.USER, user_prompt)]
        self.execute(messages, state)

    def on_retry(self, state: WorkflowState) -> None:
        pass

    def on_max_retries_exceeded(self, state: WorkflowState) -> None:
        pass

    def validate(self, result: IssueData) -> Optional[str]:
        return None

    def next_step(self, state: WorkflowState) -> NextStep:
        if state is None:
            return NextStep.END

        context = self.get_context(state)
        if context.error:
            logging.error(f"{self.agent_name} encountered an error: {context.error}")
            return NextStep.END
        return NextStep.NEXT

# src/models/agent_state_models.py

import json
import logging
import textwrap
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

from models.enums import MessageRole

T = TypeVar("T", bound=BaseModel)


class RawInputs(BaseModel):
    repo: str
    problem_statement: str
    base_commit: str


class IterationRecord(BaseModel, Generic[T]):
    prompt: str
    result: Optional[T] = None
    error: Optional[str] = None
    raw_result: Optional[dict] = None


class AgentExecutionContext(BaseModel, Generic[T]):
    iteration_history: List[IterationRecord[T]] = []
    full_history: List[IterationRecord[T]] = []
    attempts: int = 1
    max_retries: int = 3
    extra_template_vars: Dict[str, Any] = {}
    output_model: Optional[Type[T]] = None

    def set_extra_template_vars(self, vars: dict):
        self.extra_template_vars = vars

    def get_extra_template_vars(self) -> dict:
        return self.extra_template_vars

    def has_more_retries(self) -> bool:
        return self.attempts <= self.max_retries

    def handle_error(self, error_message: str, prompt: str, result: Optional[T], raw_result: Optional[dict]):
        self.attempts += 1
        record = IterationRecord[T](prompt=prompt, error=error_message, result=result, raw_result=raw_result)
        self.iteration_history.append(record)
        self.full_history.append(record)

    def add_successful_iteration(self, record: IterationRecord[T]):
        self.full_history.append(record)
        self.iteration_history.append(record)

    def reset(self):
        self.attempts = 0
        self.extra_template_vars = {}
        self.iteration_history.clear()

    def get_last_record(self) -> Optional[IterationRecord[T]]:
        if not self.full_history:
            return None

        last_record = self.full_history[-1]

        if last_record.result and isinstance(last_record.result, dict) and self.output_model:
            last_record.result = self.output_model(**last_record.result)

        return last_record

    def build_conversation_messages(self, use_full_history: bool = False) -> List[tuple[MessageRole, str]]:
        history = self.full_history if use_full_history else self.iteration_history
        messages = []

        for record in history:
            if record.prompt:
                messages.append((MessageRole.USER, record.prompt))

            if record.raw_result:
                result_str = json.dumps(record.raw_result, indent=2)
                messages.append((MessageRole.ASSISTANT, result_str))

        return messages


class WorkflowState(BaseModel):
    raw_inputs: RawInputs
    contexts: Dict[str, AgentExecutionContext[Any]] = {}
    previous_agent: Optional[str] = None

    def get_context(self, agent_name: str) -> AgentExecutionContext[Any]:
        return self.contexts.setdefault(agent_name, AgentExecutionContext())

    def copy_context(self, agent_name: str) -> AgentExecutionContext[Any]:
        context = self.get_context(agent_name).model_copy(deep=True)
        context.reset()
        return context

    def updated_context(self, agent_name: str, context: AgentExecutionContext[Any]) -> dict:
        return {
            "contexts": {agent_name: context.model_dump()},
            "previous_agent": agent_name,
        }

    def print_agent_output(self, agent_name: str) -> None:
        context = self.get_context(agent_name)
        last_record = context.get_last_record()

        separator = "=" * 60
        header = f"Agent Output: [{agent_name}]"

        if last_record is None:
            content = f"No execution history available for agent '{agent_name}'."
        elif last_record.error:
            content = textwrap.indent(f"Error:\n{last_record.error}", prefix="  ")
        elif last_record.raw_result:
            formatted_output = json.dumps(last_record.raw_result, indent=2, ensure_ascii=False)
            content = textwrap.indent(f"Output:\n{formatted_output}", prefix="  ")
        else:
            content = f"Agent '{agent_name}' produced no output."

        full_message = f"\n{separator}\n{header}\n{separator}\n{content}\n{separator}"

        logging.info(full_message)


class SWEBenchVerifiedInstance(BaseModel):
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    fail_to_pass: List[str] = Field(..., alias="FAIL_TO_PASS")
    pass_to_pass: List[str] = Field(..., alias="PASS_TO_PASS")
    environment_setup_commit: str
    difficulty: Optional[str]

    def get_raw_inputs(self) -> RawInputs:
        return RawInputs(
            repo=self.repo,
            problem_statement=self.problem_statement,
            base_commit=self.base_commit,
        )

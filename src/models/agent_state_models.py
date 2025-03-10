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
    history: List[IterationRecord[T]] = []
    attempts: int = 1
    max_retries: int = 3
    extra_template_vars: Dict[str, Any] = {}
    output_model: Optional[Type[T]] = None

    def set_extra_template_vars(self, vars: dict):
        self.extra_template_vars = vars

    def get_extra_template_vars(self) -> dict:
        return self.extra_template_vars

    def add_attempt(self) -> int:
        current_attempt = self.attempts
        self.attempts += 1
        return current_attempt

    def has_more_retries(self) -> bool:
        return self.attempts <= self.max_retries

    def handle_error(self, error_message: str, prompt: str, result: Optional[T], raw_result: Optional[dict]):
        record = IterationRecord[T](prompt=prompt, error=error_message, result=result, raw_result=raw_result)
        self.history.append(record)

    def add_successful_iteration(self, record: IterationRecord[T]):
        self.history.append(record)

    def get_last_record(self) -> Optional[IterationRecord[T]]:
        if not self.history:
            return None
        last_record = self.history[-1]
        if last_record.result and isinstance(last_record.result, dict) and self.output_model:
            last_record.result = self.output_model(**last_record.result)
        return last_record

    def build_conversation_messages(self) -> List[tuple[MessageRole, str]]:
        messages = []
        for record in self.history:
            if record.prompt:
                messages.append((MessageRole.USER, record.prompt))
            if record.raw_result:
                result_str = json.dumps(record.raw_result, indent=2)
                messages.append((MessageRole.ASSISTANT, result_str))
        return messages


class WorkflowState(BaseModel):
    raw_inputs: RawInputs
    contexts: Dict[str, List[AgentExecutionContext[Any]]] = {}
    previous_agent: Optional[str] = None

    def get_latest_context(self, agent_name: str) -> Optional[AgentExecutionContext[Any]]:
        return self.contexts.get(agent_name, [None])[-1]

    def create_new_context(self, agent_name: str, output_model: Optional[Type[T]] = None) -> AgentExecutionContext[Any]:
        new_context = AgentExecutionContext(output_model=output_model)
        self.contexts.setdefault(agent_name, []).append(new_context)
        return new_context

    def build_context_update(self, agent_name: str, context: AgentExecutionContext[Any]) -> dict:
        return {
            "contexts": {agent_name: [context.model_dump()]},
            "previous_agent": agent_name,
        }

    def print_agent_output(self, agent_name: str) -> None:
        context = self.get_latest_context(agent_name)
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

# src/models/agent_state_models.py

import json
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class RawInputs(BaseModel):
    repo: str
    problem_statement: str
    base_commit: str


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


class IterationRecord(BaseModel, Generic[T]):
    prompt: str
    result: Optional[T] = None
    error: Optional[str] = None


class AgentExecutionContext(BaseModel, Generic[T]):
    error: Optional[str] = None
    iteration_history: List[IterationRecord[T]] = []
    full_history: List[IterationRecord[T]] = []
    attempts: int = 0
    max_retries: int = 3

    def has_more_retries(self) -> bool:
        """Check if there are more retries available."""
        return self.attempts < self.max_retries

    def handle_error(self, error_message: str, prompt: str):
        """Handle an error by recording it and incrementing attempts."""
        self.error = error_message
        self.attempts += 1

        record = IterationRecord[T](prompt=prompt, error=error_message)
        self.iteration_history.append(record)
        self.full_history.append(record)

    def add_successful_iteration(self, record: IterationRecord[T]):
        """Add a successful iteration record."""
        self.full_history.append(record)
        self.error = None

    def reset(self):
        """Reset the context for a new execution."""
        self.error = None
        self.attempts = 0
        self.iteration_history.clear()

    def get_last_record(self) -> Optional[IterationRecord[T]]:
        """Returns the last iteration record, if available."""
        return self.full_history[-1] if self.full_history else None


class WorkflowState(BaseModel):
    raw_inputs: RawInputs
    contexts: Dict[str, AgentExecutionContext[Any]] = {}
    previous_agent: Optional[str] = None

    def get_context(self, agent_name: str) -> AgentExecutionContext[Any]:
        """Get or create an execution context for an agent."""
        return self.contexts.setdefault(agent_name, AgentExecutionContext())

    def set_previous_agent(self, agent_name: str):
        """Set the previous agent name."""
        self.previous_agent = agent_name

    def print_agent_output(self, agent_name: str) -> None:
        """Print the output or error for a specific agent."""
        context = self.get_context(agent_name)
        last_record = context.get_last_record()

        print(f"\n=== Node: {agent_name} ===\n")

        if last_record is None:
            print("No execution history available.")
        elif last_record.error:
            print(f"Error: {last_record.error}")
        elif last_record.result:
            print(json.dumps(last_record.result.model_dump(), indent=2))
        else:
            print("No output available.")

        print("=" * 40)

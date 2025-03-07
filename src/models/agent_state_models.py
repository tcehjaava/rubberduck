# src/models/agent_state_models.py

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class RawInputs(BaseModel):
    repo: str
    problem_statement: str
    base_commit: str


class IterationRecord(Generic[T], BaseModel):
    prompt: str
    result: Optional[T] = None
    error: Optional[str] = None


class AgentExecutionContext(Generic[T], BaseModel):
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

# src/agents/base_agent.py

import json
from typing import Generic, List, Optional, TypeVar

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError

from config.config_models import AgentConfig
from models import (
    AgentExecutionContext,
    IterationRecord,
    MessageRole,
    NextStep,
    WorkflowState,
)
from utils.llm_factory import LLMFactory

T = TypeVar("T", bound=BaseModel)


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseAgent(Generic[T], metaclass=SingletonMeta):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = LLMFactory.get_llm_from_config(config)
        self.agent_name = self.__class__.__name__

        for base in self.__class__.__orig_bases__:
            if hasattr(base, "__origin__") and base.__origin__ is BaseAgent:
                self.output_model = base.__args__[0]
                break
        else:
            raise TypeError(f"Could not determine output model type for {self.__class__.__name__}")

        self.parser = JsonOutputParser(pydantic_object=self.output_model)

    def get_context(self, state: WorkflowState) -> AgentExecutionContext[T]:
        return state.get_context(self.agent_name)

    def execute(self, messages: List[tuple[MessageRole, str]], state: WorkflowState) -> None:
        context = self.get_context(state)

        # Convert to langchain message format and prepend system prompt
        formatted_messages = [(MessageRole.SYSTEM, f"{self.config.SYSTEM_PROMPT}\n\n{{format_instructions}}")]
        formatted_messages.extend([(role.value, content) for role, content in messages])

        prompt = ChatPromptTemplate.from_messages(formatted_messages)
        chain = prompt | self.llm | self.parser

        user_prompt = next((content for role, content in messages if role == MessageRole.USER), "")

        try:
            raw_result = chain.invoke({"format_instructions": self.parser.get_format_instructions()})
            result = self.output_model(**raw_result)

            validation_error = self.validate(result)
            if validation_error is None:
                record = IterationRecord[T](prompt=user_prompt, result=result)
                context.add_successful_iteration(record)
                state.set_previous_agent(self.agent_name)
            else:
                raise ValidationError(validation_error, self.output_model)

        except Exception as e:
            context.handle_error(str(e), user_prompt)

            if not context.has_more_retries():
                self.on_max_retries_exceeded(state)
            else:
                self.on_retry(state)

        context.reset()

    def run(self, state: WorkflowState) -> None:
        raise NotImplementedError("Subclasses must implement run method.")

    def on_retry(self, state: WorkflowState) -> None:
        raise NotImplementedError("Subclasses must implement on_retry method.")

    def on_max_retries_exceeded(self, state: WorkflowState) -> None:
        raise NotImplementedError("Subclasses must implement on_max_retries_exceeded method.")

    def validate(self, result: T) -> Optional[str]:
        raise NotImplementedError("Subclasses must implement validate method.")

    def next_step(self, state: WorkflowState) -> NextStep:
        raise NotImplementedError("Implement the workflow next step decision logic")

    def print_output(self, state: WorkflowState) -> None:
        print(f"\n=== Node: {self.agent_name} ===\n")

        context = self.get_context(state)
        if not context.full_history:
            print("No execution history available.")
        else:
            last_record = context.full_history[-1]

            if last_record.error:
                print(f"Error: {last_record.error}")
            elif last_record.result:
                print(json.dumps(last_record.result.model_dump(), indent=2))
            else:
                print("No output available.")

        print("=" * 40)

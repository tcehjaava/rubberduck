import logging
from typing import Generic, List, Optional, TypeVar

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from rubberduck.langgraph.graph_orchestrator.config.config_models import AgentConfig
from rubberduck.langgraph.graph_orchestrator.models import (
    AgentExecutionContext,
    IterationRecord,
    MessageRole,
    NextStep,
    WorkflowState,
)
from rubberduck.langgraph.graph_orchestrator.utils.llm_factory import LLMFactory

T = TypeVar("T", bound=BaseModel)


class BaseAgent(Generic[T]):
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

    def create_context(self, state: WorkflowState) -> AgentExecutionContext[T]:
        return state.create_new_context(self.agent_name, self.output_model)

    def execute(self, messages: List[tuple[MessageRole, str]], context: AgentExecutionContext[T]) -> None:
        iteration = context.add_attempt()
        logging.info(f"[{self.agent_name}] Starting execute (Iteration: {iteration})")

        extra_vars = context.get_extra_template_vars()
        formatted_system_prompt = self.config.SYSTEM_PROMPT.format(**extra_vars)
        format_instructions = self.parser.get_format_instructions()
        system_prompt = f"{formatted_system_prompt}\n\n{format_instructions}"

        formatted_messages = [
            SystemMessage(content=system_prompt),
            *[
                (HumanMessage(content) if role == MessageRole.USER else AIMessage(content))
                for role, content in messages
                if role != MessageRole.SYSTEM
            ],
        ]

        prompt = ChatPromptTemplate.from_messages(formatted_messages)
        chain = prompt | self.llm | self.parser

        user_prompt = next((content for role, content in reversed(messages) if role == MessageRole.USER), "")

        raw_result, result = None, None
        try:
            raw_result = chain.invoke({})
            result = self.output_model(**raw_result)

            validation_error = self.validate(context, result)
            if validation_error is None:
                record = IterationRecord[T](prompt=user_prompt, result=result, raw_result=raw_result)
                context.add_successful_iteration(record)
            else:
                raise ValueError(validation_error, self.output_model)
        except Exception as e:
            error_message = str(e)
            logging.error(f"[{self.agent_name}] Error encountered on iteration {iteration}: {error_message}")
            context.handle_error(error_message, user_prompt, result, raw_result)

            if not context.has_more_retries():
                logging.warning(f"[{self.agent_name}] Max retries ({context.max_retries}) exceeded.")
                self.on_max_retries_exceeded(context)
            else:
                self.on_retry(context)

    def run(self, state: WorkflowState) -> dict:
        raise NotImplementedError("Subclasses must implement run method.")

    def on_retry(self, context: AgentExecutionContext[T]) -> None:
        raise NotImplementedError("Subclasses must implement on_retry method.")

    def on_max_retries_exceeded(self, context: AgentExecutionContext[T]) -> None:
        raise NotImplementedError("Subclasses must implement on_max_retries_exceeded method.")

    def validate(self, context: AgentExecutionContext[T], result: T) -> Optional[str]:
        raise NotImplementedError("Subclasses must implement validate method.")

    def next_step(self, state: WorkflowState) -> NextStep:
        raise NotImplementedError("Implement the workflow next step decision logic")

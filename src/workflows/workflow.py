# src/workflows/workflow.py

from langgraph.graph import END, StateGraph

from src.agents import (
    IssueDataExtractorAgent,
    issue_data_extractor_config,
)
from src.models import NextStep, WorkflowState


class WorkflowBuilder:

    @staticmethod
    def create_workflow() -> StateGraph:
        workflow = StateGraph(WorkflowState)

        issue_data_extractor = IssueDataExtractorAgent(config=issue_data_extractor_config)

        workflow.add_node(IssueDataExtractorAgent.__name__, issue_data_extractor.run)

        workflow.set_entry_point(IssueDataExtractorAgent.__name__)

        workflow.add_conditional_edges(
            IssueDataExtractorAgent.__name__,
            issue_data_extractor.next_step,
            {NextStep.NEXT.value: END, NextStep.END.value: END},
        )

        return workflow.compile()

    @staticmethod
    def run(initial_state: WorkflowState):
        workflow = WorkflowBuilder.create_workflow()

        for output in workflow.stream(initial_state):
            for agent, state in output.items():
                state.print_agent_output(state.previous_agent)

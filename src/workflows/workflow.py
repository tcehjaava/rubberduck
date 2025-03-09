# src/workflows/workflow.py

from langgraph.graph import END, StateGraph

from agents import Orchestrator, orchestrator_config
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
        orchestrator = Orchestrator(config=orchestrator_config)

        workflow.add_node(IssueDataExtractorAgent.__name__, issue_data_extractor.run)
        workflow.add_node(Orchestrator.__name__, orchestrator.run)

        workflow.add_conditional_edges(
            IssueDataExtractorAgent.__name__,
            issue_data_extractor.next_step,
            {
                NextStep.NEXT.value: Orchestrator.__name__,
                NextStep.END.value: END,
            },
        )

        workflow.add_conditional_edges(
            Orchestrator.__name__,
            orchestrator.next_step,
            {
                NextStep.NEXT.value: END,
                NextStep.END.value: END,
            },
        )

        workflow.set_entry_point(IssueDataExtractorAgent.__name__)
        return workflow.compile()

    @staticmethod
    def run(initial_state: WorkflowState):
        workflow = WorkflowBuilder.create_workflow()
        current_state_dict = initial_state.model_dump()

        for output in workflow.stream(current_state_dict):
            for agent, partial_update in output.items():
                current_state_dict.update(partial_update)
                current_state = WorkflowState.model_validate(current_state_dict)
                current_state.print_agent_output(agent)

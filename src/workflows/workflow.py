# src/workflows/workflow.py

from langgraph.graph import END, StateGraph

from agents import (
    IssueDataExtractorAgent,
    Orchestrator,
    QueryBuilderAgent,
    issue_data_extractor_config,
    orchestrator_config,
    query_builder_config,
)
from models import NextStep, WorkflowState
from utils import WorkflowLogger


class WorkflowBuilder:

    @staticmethod
    def create_workflow() -> StateGraph:
        workflow = StateGraph(WorkflowState)

        issue_data_extractor = IssueDataExtractorAgent(config=issue_data_extractor_config)
        orchestrator = Orchestrator(config=orchestrator_config)
        query_builder = QueryBuilderAgent(config=query_builder_config)

        workflow.add_node(IssueDataExtractorAgent.__name__, issue_data_extractor.run)
        workflow.add_node(Orchestrator.__name__, orchestrator.run)
        workflow.add_node(QueryBuilderAgent.__name__, query_builder.run)

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
                NextStep.NEXT.value: QueryBuilderAgent.__name__,
                NextStep.END.value: END,
            },
        )

        workflow.add_conditional_edges(
            QueryBuilderAgent.__name__,
            query_builder.next_step,
            {
                NextStep.NEXT.value: END,
                NextStep.END.value: END,
            },
        )

        workflow.set_entry_point(IssueDataExtractorAgent.__name__)
        return workflow.compile()

    @staticmethod
    def run(initial_state: WorkflowState) -> WorkflowState:
        workflow = WorkflowBuilder.create_workflow()
        current_state_dict = initial_state.model_dump()

        for output in workflow.stream(current_state_dict):
            for agent, partial_update in output.items():
                current_state_dict.update(partial_update)
                current_state = WorkflowState.model_validate(current_state_dict)
                WorkflowLogger.print_agent_output(current_state, agent)

        return current_state

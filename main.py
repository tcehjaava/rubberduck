import logging
import uuid

from rubberduck.langgraph.graph_orchestrator.config import GLOBAL_CONFIG, LoggingConfig
from rubberduck.langgraph.graph_orchestrator.models import WorkflowState
from rubberduck.langgraph.graph_orchestrator.utils import DatasetUtils, WorkflowLogger
from rubberduck.langgraph.graph_orchestrator.workflows import WorkflowBuilder


def main(instance_id: str):
    run_id = uuid.uuid4().hex[:8]
    agents_log_dir = LoggingConfig.setup_run_logging(run_id=run_id)
    logging.info(f"Starting workflow run: {run_id} for instance: {instance_id}")

    instance = DatasetUtils.load_instance(instance_id)
    assert instance is not None

    raw_inputs = instance.get_raw_inputs()
    initial_state = WorkflowState(raw_inputs=raw_inputs)

    workflow_state = WorkflowBuilder.run(initial_state)
    WorkflowLogger.log_all_agents_history(workflow_state, agents_log_dir)


if __name__ == "__main__":
    main(GLOBAL_CONFIG.INSTANCE_ID)

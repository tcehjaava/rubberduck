import argparse
import uuid

from rubberduck.autogen.leader_executor.models.swebench_workflow import (
    SWEBenchWorkflowNode,
)
from rubberduck.autogen.leader_executor.utils.logger import dump_memory, setup_logger
from rubberduck.autogen.leader_executor.workflows.swebench import SWEBenchWorkflow

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leader-Executor agent system runner")
    parser.add_argument("instance_id", type=str, help="Instance ID to process")

    args = parser.parse_args()

    run_id = str(uuid.uuid4())
    logger, log_dir = setup_logger(run_id=run_id)
    logger.info(f"Starting Leader-Executor agent system... 📋 Run ID: {run_id}")

    final_state = SWEBenchWorkflow().run(args.instance_id, thread_id=run_id)
    logger.info(f"Completed processing for {args.instance_id}")

    dump_memory(
        final_state.get("memory", {}), log_dir, [SWEBenchWorkflowNode.INIT.value, SWEBenchWorkflowNode.REPO_CLONE.value]
    )

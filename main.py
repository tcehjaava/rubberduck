import argparse
import uuid

from utils.dataset_utils import DatasetUtils

from rubberduck.utils.logger import setup_logger
from rubberduck.workflows.swebench import SWEBenchWorkflow

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leader-Executor agent system runner")
    parser.add_argument("instance_id", type=str, help="Instance ID to process")

    args = parser.parse_args()

    run_id = str(uuid.uuid4())
    logger, log_dir = setup_logger(run_id=run_id)
    logger.info(f"Starting Leader-Executor agent system... 📋 Run ID: {run_id}")

    final_state = SWEBenchWorkflow().run(args.instance_id, thread_id=run_id)
    logger.info(f"Completed processing for {args.instance_id}")

    instance = DatasetUtils.load_instance(instance_id=args.instance_id)
    logger.info(f"Actual SWEBench dataset patch: {instance.patch}")

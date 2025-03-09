# main.py

import logging
import uuid

from config import GLOBAL_CONFIG, LoggingConfig
from models import WorkflowState
from utils.dataset_utils import DatasetUtils
from workflows import WorkflowBuilder


def main(instance_id: str):
    run_id = uuid.uuid4().hex[:8]
    LoggingConfig.setup_run_logging(run_id=run_id)
    logging.info(f"Starting workflow run: {run_id} for instance: {instance_id}")

    instance = DatasetUtils.load_instance(instance_id)
    assert instance is not None

    raw_inputs = instance.get_raw_inputs()
    initial_state = WorkflowState(raw_inputs=raw_inputs)

    WorkflowBuilder.run(initial_state)


if __name__ == "__main__":
    main(GLOBAL_CONFIG.INSTANCE_ID)

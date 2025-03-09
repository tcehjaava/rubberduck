# main.py

import logging

from config import GLOBAL_CONFIG
from models import WorkflowState
from utils.dataset_utils import DatasetUtils
from workflows import WorkflowBuilder

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main(instance_id: str):
    instance = DatasetUtils.load_instance(instance_id)
    assert instance is not None

    raw_inputs = instance.get_raw_inputs()
    initial_state = WorkflowState(raw_inputs=raw_inputs)

    WorkflowBuilder.run(initial_state)


if __name__ == "__main__":
    main(GLOBAL_CONFIG.INSTANCE_ID)

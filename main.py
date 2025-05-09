import shutil
import uuid
from contextlib import suppress

from rubberduck.autogen.leader_executor.agents import ExecutorAgent
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor
from rubberduck.autogen.leader_executor.utils import RepoCloner
from rubberduck.autogen.leader_executor.utils.logger import setup_logger
from rubberduck.langgraph.graph_orchestrator.utils import DatasetUtils


def main(instance_id: str):
    instance = DatasetUtils.load_instance(instance_id)
    if instance is None:
        raise ValueError(f"Instance '{instance_id}' not found")

    try:
        with RepoDockerExecutor(instance) as repo_executor:
            RepoCloner(repo_executor).clone(instance)
            agent = ExecutorAgent(repo_executor, instance)
            agent.perform_task(
                """
Now I need to see how the actual TestCaseFunction.runtest method is implemented to understand how it handles both skipped tests and the --pdb option together.

Task 11: Let's view the complete TestCaseFunction class implementation:

```bash
cat src/_pytest/unittest.py | sed -n '/class TestCaseFunction/,/^\s*class /p'
```
"""
            )
    finally:
        if repo_executor is not None:
            with suppress(FileNotFoundError):
                shutil.rmtree(repo_executor.host_code_execution_dir)


if __name__ == "__main__":
    logger, log_path = setup_logger(run_id=str(uuid.uuid4()))
    logger.info("Starting executor agent...")
    # main("pytest-dev__pytest-7236")

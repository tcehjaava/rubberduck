import shutil
import time
from contextlib import suppress

from rubberduck.autogen.leader_executor.agents import ExecutorAgent
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor
from rubberduck.autogen.leader_executor.utils import RepoCloner
from rubberduck.langgraph.graph_orchestrator.utils import DatasetUtils


def main(instance_id: str):
    instance = DatasetUtils.load_instance(instance_id)
    if instance is None:
        raise ValueError(f"Instance '{instance_id}' not found")

    try:
        with RepoDockerExecutor(instance) as repo_executor:
            RepoCloner(repo_executor).clone(instance.repo)
            agent = ExecutorAgent(repo_executor)
            agent.perform_task("Run tests and see if everything is working fine")
            time.sleep(10)
    finally:
        if repo_executor is not None:
            with suppress(FileNotFoundError):
                shutil.rmtree(repo_executor.host_code_execution_dir)


if __name__ == "__main__":
    main("pytest-dev__pytest-7236")

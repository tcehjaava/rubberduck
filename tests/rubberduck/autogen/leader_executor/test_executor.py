import logging

from rubberduck.autogen.leader_executor.agents.executor import ExecutorAgent
from rubberduck.autogen.leader_executor.utils.container_manager import ContainerManager

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    instance = "pydata__xarray-3095"

    with ContainerManager(instance) as cm:
        agent = ExecutorAgent(instance, cm)
        agent.perform_task(
            "In /workspace/xarray:\n"
            "1. list *.md\n"
            "2. show README.md\n"
            "3. does it have installation instructions? if yes, print them."
        )

import tempfile
from pathlib import Path

import docker
from autogen.coding import DockerCommandLineCodeExecutor
from docker.errors import NotFound as DockerNotFound
from loguru import logger

from rubberduck.autogen.leader_executor.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)


class RepoDockerExecutor(DockerCommandLineCodeExecutor):
    def __init__(self, instance: SWEBenchVerifiedInstance, image: str = "python:3.10-slim"):
        self.instance = instance
        sanitized_repo_name = self.instance.repo.replace("/", "_").replace(":", "_")
        self.container_name = f"swebench-{sanitized_repo_name}-{self.instance.instance_id}"

        self.host_code_execution_dir = Path(
            tempfile.mkdtemp(prefix=f"swe-{sanitized_repo_name}-{self.instance.instance_id}-")
        ).resolve()

        logger.info(
            f"Initialized RepoDockerExecutor at directory {self.host_code_execution_dir} (mounted to '/workspace' in"
            "container)"
        )

        try:
            client = docker.from_env()
            container = client.containers.get(self.container_name)
            logger.info(f"Removing pre-existing container: {self.container_name}")
            container.stop(timeout=5)
            container.remove(force=True)
        except DockerNotFound:
            logger.debug(f"No pre-existing container named {self.container_name} found.")
        except Exception as e:
            logger.warning(
                f"Error while trying to stop pre-existing container {self.container_name}: {e}", exc_info=True
            )

        super().__init__(
            image=image,
            container_name=self.container_name,
            work_dir=self.host_code_execution_dir,
            bind_dir=self.host_code_execution_dir,
            timeout=1800,
        )

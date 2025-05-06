import logging

import docker
from docker.models.containers import Container

from rubberduck.autogen.leader_executor.models import SWEBenchVerifiedInstance
from rubberduck.autogen.leader_executor.utils.dataset_utils import DatasetUtils


class Setup:
    def __init__(self, instance_id: str, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.client = docker.from_env()
        self.instance: SWEBenchVerifiedInstance = self._load_instance(instance_id)
        self.container_name = f"swebench-{self.instance.repo.replace('/', '-')}-{self.instance.instance_id}"
        self.image_name = "python:3.11-slim"
        self.container: Container = None

    def _load_instance(self, instance_id: str) -> SWEBenchVerifiedInstance:
        self.logger.info(f"Loading instance: {instance_id}")
        instance_data = DatasetUtils.load_instance(instance_id)
        if instance_data is None:
            raise ValueError(f"Instance with ID '{instance_id}' not found in the dataset")
        return instance_data

    def _create_container(self):
        self.cleanup()

        self.logger.info(f"Creating container: {self.container_name}")
        self.container = self.client.containers.run(
            self.image_name, name=self.container_name, command="sleep infinity", detach=True, tty=True
        )

    def _exec_command(self, command: str, workdir: str = "/workspace"):
        if not self.container:
            raise RuntimeError("Container is not created or has been cleaned up.")

        self.logger.info(f"Executing command: {command}")
        exec_log = self.container.exec_run(cmd=command, workdir=workdir, stream=True)
        for line in exec_log.output:
            log_line = line.decode().strip()
            if log_line:
                self.logger.info(f"Command output: {log_line}")

    def _install_git(self):
        self.logger.info("Installing git...")
        self._exec_command("apt-get update && apt-get install -y git")

    def _clone_and_checkout(self):
        repo_id = self.instance.repo
        commit_hash = self.instance.base_commit
        self.logger.info(f"Cloning repo: {repo_id}, checkout commit: {commit_hash}")

        github_url = f"https://github.com/{repo_id}.git"
        cmd = f"git clone {github_url} repo && cd repo && git checkout {commit_hash}"
        self._exec_command(cmd)

    def setup_environment(self):
        self.logger.info(f"Setting up environment for instance {self.instance.instance_id}")
        self._create_container()
        self._install_git()
        self._clone_and_checkout()
        self.logger.info(f"Environment setup complete for instance {self.instance.instance_id}")

    def cleanup(self):
        existing_containers = self.client.containers.list(all=True, filters={"name": self.container_name})

        for container in existing_containers:
            self.logger.info(f"Cleaning up container: {self.container_name}")
            if container.status == "running":
                container.stop()
            container.remove()

        self.container = None

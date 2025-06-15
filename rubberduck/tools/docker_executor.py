import os
import tempfile
from pathlib import Path

import docker
from autogen.coding import DockerCommandLineCodeExecutor
from docker.errors import ImageNotFound
from docker.errors import NotFound as DockerNotFound
from loguru import logger
from swebench.harness.docker_build import build_instance_images
from swebench.harness.test_spec.test_spec import make_test_spec

from rubberduck.autogen.leader_executor.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)


class RepoDockerExecutor(DockerCommandLineCodeExecutor):
    def __init__(self, instance: SWEBenchVerifiedInstance):
        client = docker.from_env()

        spec = make_test_spec(instance=instance.model_dump())
        image = spec.instance_image_key
        logger.info(f"Using image {image}")

        try:
            client.images.get(image)
            logger.info(f"Image {image} already cached – skipping build.")
        except ImageNotFound:
            logger.info(f"Building missing image {image} – this is one-time.")
            build_instance_images(dataset=[spec], client=client)

        container_name = f"swe-{instance.instance_id}"
        work_dir = Path(tempfile.mkdtemp(prefix=f"{container_name}-"))

        try:
            container = client.containers.get(container_name)
            logger.info(f"Removing pre-existing container: {container_name}")
            container.stop(timeout=5)
            container.remove(force=True)
        except DockerNotFound:
            logger.debug(f"No pre-existing container named {container_name} found.")

        container = client.containers.run(
            image=image,
            name=container_name,
            command=["sleep", "3600"],  # keep the container alive 1 h
            detach=True,
            tty=True,
            # volumes=[f"{work_dir.as_posix()}:/testbed:rw"],
            working_dir="/testbed",
            environment={"PYTHONUNBUFFERED": "1"},
        )
        logger.info(f"Initialized RepoDockerExecutor at directory {work_dir} (mounted to '/testbed' in container)")

        uid, gid = os.getuid(), os.getgid()
        container.exec_run(["chown", "-R", f"{uid}:{gid}", "/testbed"], user="root")
        container.exec_run(["chmod", "-R", "a+rX", "/testbed"], user="root")
        container.exec_run(
            [
                "bash",
                "-c",
                "git config --global user.email 'tejachava80@gmail.com' && "
                "git config --global user.name 'tejachava80' && "
                "git config --global --add safe.directory /testbed && "
                "git -C /testbed commit --allow-empty -m init",
            ],
            user="root",
        )
        logger.info("Workspace permissions fixed inside container.")

        # Add this after container creation, before running tests
        result = container.exec_run(
            [
                "bash",
                "-c",
                "source /opt/miniconda3/bin/activate testbed && pytest -q",
            ],
            workdir="/testbed",
            tty=True,
        )
        logger.info(f"Baseline test output:\n{result.output.decode()}")

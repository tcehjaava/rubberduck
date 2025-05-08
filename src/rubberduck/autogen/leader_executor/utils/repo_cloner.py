import logging
from pathlib import Path

from autogen.coding import DockerCommandLineCodeExecutor

logger = logging.getLogger(__name__)


class RepoCloner:
    def __init__(self, executor: DockerCommandLineCodeExecutor):
        self.executor = executor
        self._container_workdir = "/workspace"

    def clone(self, repo: str) -> str:
        if not repo:
            raise ValueError("Repository identifier (repo) cannot be empty.")

        repo_subdir_name = repo.rstrip("/").split("/")[-1]
        if not repo_subdir_name:
            raise ValueError(f"Could not determine repository subdirectory name from '{repo}'")

        repo_url = f"https://github.com/{repo}.git"

        cloned_repo_on_container_path = Path(self._container_workdir) / repo_subdir_name

        script = f"""
set -e

echo "INFO: Starting repository cloning process..."
echo "INFO: Repository URL: {repo_url}"
echo "INFO: Target in-container directory: {cloned_repo_on_container_path}"
echo "INFO: Executor's host work_dir (bind_dir for container): {self.executor.work_dir}"

echo "INFO: Updating package list and installing git..."
apt-get update -q -y
DEBIAN_FRONTEND=noninteractive apt-get install -q -y git

cd "{self._container_workdir}"
echo "INFO: Current directory inside container for cloning: $(pwd)"

if [ -d "{repo_subdir_name}" ]; then
    echo "INFO: Directory '{repo_subdir_name}' already exists. Removing it for a clean clone."
    rm -rf "{repo_subdir_name}"
fi

echo "INFO: Cloning repository..."
git clone --depth 1 "{repo_url}" "{repo_subdir_name}"

echo "INFO: Listing contents of the cloned directory ({cloned_repo_on_container_path}):"
ls -la "{repo_subdir_name}"

echo "INFO: Cloning process finished."
"""
        result = self.executor._container.exec_run(cmd=["sh", "-c", script], workdir=self._container_workdir)

        output_log = result.output.decode(errors="replace")

        if result.exit_code != 0:
            error_message = (
                f"Failed to clone repo '{repo}' into '{cloned_repo_on_container_path}' "
                f"inside container '{self.executor._container.name}'.\n"
                f"Exit code: {result.exit_code}\n"
                f"Output:\n{output_log}"
            )
            logger.error(error_message)
            raise RuntimeError(error_message)

        logger.info(
            f"Successfully cloned '{repo}' into '{cloned_repo_on_container_path}' "
            f"inside container '{self.executor._container.name}'.\nScript output was:\n{output_log}"
        )

        return output_log

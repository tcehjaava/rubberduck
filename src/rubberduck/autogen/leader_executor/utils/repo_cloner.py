from autogen.coding import CodeBlock, DockerCommandLineCodeExecutor

from rubberduck.autogen.leader_executor.models.swebench import SWEBenchVerifiedInstance


class RepoCloner:
    def __init__(self, executor: DockerCommandLineCodeExecutor):
        self.executor = executor
        self._container_workdir = "/workspace"

    def clone(self, instance: SWEBenchVerifiedInstance) -> str:
        repo_subdir_name = instance.repo_subdir_name

        script = f"""
        set -e

        apt-get update -q -y
        DEBIAN_FRONTEND=noninteractive apt-get install -q -y git

        cd "{self._container_workdir}"

        rm -rf "ast_grep_rules"
        rm -rf "{repo_subdir_name}"
        git clone --depth 1 "https://github.com/{instance.repo}.git" "{repo_subdir_name}"

        cd "{repo_subdir_name}"
        git fetch --unshallow
        git checkout -b "{instance.instance_id}" "{instance.base_commit}"
        """

        block = CodeBlock(language="bash", code=script)
        result = self.executor.execute_code_blocks([block])

        if result.exit_code != 0:
            raise RuntimeError(f"Failed to clone repo '{instance.repo}'.\nOutput:\n{result.output}")

        return result.output

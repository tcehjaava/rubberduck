from pathlib import Path

from autogen.coding import DockerCommandLineCodeExecutor

from rubberduck.autogen.leader_executor.models.swebench import SWEBenchVerifiedInstance


class RepoCloner:
    def __init__(self, executor: DockerCommandLineCodeExecutor):
        self.executor = executor
        self._container_workdir = "/workspace"

    def clone(self, instance: SWEBenchVerifiedInstance) -> str:
        repo_subdir_name = instance.repo_subdir_name
        helper_code = Path(__file__).with_name("ast_helper.py").read_text()
        xforms_code = Path(__file__).with_name("transformations.py").read_text()

        script = f"""
        set -e

        apt-get update -q -y
        DEBIAN_FRONTEND=noninteractive apt-get install -q -y git

        cd "{self._container_workdir}"

        rm -rf "{repo_subdir_name}"
        git clone --depth 1 "https://github.com/{instance.repo}.git" "{repo_subdir_name}"

        cd "{repo_subdir_name}"
        git fetch --unshallow
        git checkout -b "{instance.instance_id}" "{instance.base_commit}"

        # ---- drop helper into /workspace/helpers -----------------------------
        rm -rf "{self._container_workdir}/helpers"
        mkdir -p "{self._container_workdir}/helpers"

        cat > "{self._container_workdir}/helpers/ast_helper.py" <<'PY_AH'
{helper_code}
PY_AH

        cat > "{self._container_workdir}/helpers/transformations.py" <<'PY_XF'
{xforms_code}
PY_XF

        python3 -m py_compile "{self._container_workdir}/helpers/ast_helper.py"
        python3 -m py_compile "{self._container_workdir}/helpers/transformations.py"
        """

        result = self.executor._container.exec_run(cmd=["sh", "-c", script], workdir=self._container_workdir)

        output_log = result.output.decode(errors="replace")

        if result.exit_code != 0:
            raise RuntimeError(f"Failed to clone repo '{instance.repo}'.\nOutput:\n{output_log}")

        return output_log

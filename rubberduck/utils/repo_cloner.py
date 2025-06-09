import shlex
from pathlib import Path

from autogen.coding import CodeBlock, DockerCommandLineCodeExecutor
from tenacity import retry, stop_after_attempt, wait_exponential

from rubberduck.autogen.leader_executor.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)


class RepoCloner:
    def __init__(self, executor: DockerCommandLineCodeExecutor):
        self.executor = executor
        self._container_workdir = "/workspace"
        self._resources_dir = Path(__file__).parent.parent / "resources"

    def _get_script_content(self, script_name: str) -> str:
        script_path = self._resources_dir / script_name
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        return script_path.read_text()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=5), reraise=True)
    def clone(self, instance: SWEBenchVerifiedInstance) -> str:
        repo_subdir_name = instance.repo_subdir_name

        fail_nodes_array = "(" + " ".join(shlex.quote(n) for n in instance.fail_to_pass) + ")"
        pass_nodes_array = "(" + " ".join(shlex.quote(n) for n in instance.pass_to_pass) + ")"

        run_collect_content = self._get_script_content("run_collect.sh")
        run_tests_content = self._get_script_content("run_tests.sh")

        cherry_pick_snippet = ""
        if instance.environment_setup_commit and instance.environment_setup_commit != instance.base_commit:
            cherry_pick_snippet = (
                f'git cherry-pick --allow-empty --keep-redundant-commits "{instance.environment_setup_commit}"'
            )

        script = f"""\
set -e

apt-get update -q -y
DEBIAN_FRONTEND=noninteractive apt-get install -q -y git

git config --global user.name  "tejachava80"
git config --global user.email "tejachava80@gmail.com"

cd {self._container_workdir}

rm -rf ast_grep_rules && mkdir ast_grep_rules
rm -rf {repo_subdir_name}
git clone --depth 1 "https://github.com/{instance.repo}.git" "{repo_subdir_name}"

cd {repo_subdir_name}
git fetch --unshallow
git checkout -b "{instance.instance_id}" "{instance.base_commit}"
{cherry_pick_snippet}

cat > tests.env <<'EOF'
FAIL_TO_PASS_NODES={fail_nodes_array}
PASS_TO_PASS_NODES={pass_nodes_array}
EOF

cat > run_collect.sh <<'EOF'
{run_collect_content}
EOF
chmod +x run_collect.sh

cat > run_tests.sh <<'EOF'
{run_tests_content}
EOF
chmod +x run_tests.sh
"""

        block = CodeBlock(language="bash", code=script)
        result = self.executor.execute_code_blocks([block])

        if result.exit_code != 0:
            raise RuntimeError(f"Failed to clone repo '{instance.repo}'.\nOutput:\n{result.output}")

        return result.output

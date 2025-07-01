import io
import tarfile
import uuid
from pathlib import Path

import docker
from docker.errors import ImageNotFound
from docker.errors import NotFound as DockerNotFound
from docker.models.containers import Container
from loguru import logger
from swebench.harness.docker_build import build_container, build_instance_images
from swebench.harness.test_spec.test_spec import make_test_spec

from rubberduck.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)

_COMMAND_TIMEOUT = 300
_TESTBED = "/testbed"


def _get_file_content(file_name: str) -> str:
    script_path = Path(__file__).parent.parent / "resources" / file_name
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    return script_path.read_text()


def tar_bytes(name: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def run_script_in_container(
    container: Container,
    script_text: str,
    conda_neutral: bool = False,
    delete_after_run: bool = True,
):
    script_name = f"script-{uuid.uuid4().hex[:8]}.sh"
    archive = tar_bytes(script_name, script_text.encode())
    container.put_archive(_TESTBED, archive)

    container.exec_run(["chmod", "+x", f"{_TESTBED}/{script_name}"], user="root")

    if conda_neutral:
        env = {"CONDA_PREFIX": "", "CONDA_DEFAULT_ENV": "", "PYTHONPATH": ""}
        cmd = [f"{_TESTBED}/{script_name}"]
    else:
        cmd = ["bash", "-lc", f"{_TESTBED}/{script_name}"]
        env = None

    cmd = ["timeout", str(_COMMAND_TIMEOUT)] + cmd

    exit_code, output = container.exec_run(
        cmd,
        user="root",
        workdir=_TESTBED,
        tty=True,
        environment=env,
    )

    if delete_after_run:
        container.exec_run(["rm", "-f", f"{_TESTBED}/{script_name}"], user="root")

    return exit_code, output.decode()


def apply_patch_script() -> str:
    return rf"""#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=/opt/py311env
PY=$(command -v python3.11 || command -v python3 || true)
[[ -z "$PY" ]] && {{ echo "[apply_patch] python not found" >&2; exit 127; }}

[[ -d "$VENV_DIR" ]] || {{ "$PY" -m venv "$VENV_DIR"; "$VENV_DIR/bin/pip" install -q --no-cache-dir --upgrade pip; }}

install -d /usr/local/lib
cat >/usr/local/lib/apply_patch.py <<'AP_EOF'
{_get_file_content("apply_patch.py")}
AP_EOF

cat >/usr/local/bin/apply_patch <<'SH_EOF'
#!/usr/bin/env bash
exec env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONPATH /opt/py311env/bin/python /usr/local/lib/apply_patch.py "$@"
SH_EOF
chmod +x /usr/local/bin/apply_patch
"""


def bootstrap_script(instance: SWEBenchVerifiedInstance, ws_repo: str = _TESTBED) -> str:
    return rf"""#!/usr/bin/env bash
set -euo pipefail

# Install dependencies
echo "Installing GitPython..."
pip install --no-cache-dir GitPython --root-user-action=ignore

# Update .gitignore to exclude generated files
echo "Updating .gitignore..."
cat >> "{ws_repo}/.gitignore" <<'GITIGNORE_EOF'

# SWEBench test files
script-*.sh
.swebench_initial_commit
GITIGNORE_EOF

# Commit any existing changes (like .gitignore)
cd {ws_repo}
git add -A
git commit -m "Bootstrap: Updated .gitignore" || true

# Create an empty reference commit
# This marks the exact point where the agent starts working
git commit --allow-empty -m "[SWEBENCH-REF] Agent work starts here"

# Save the reference commit hash
git rev-parse HEAD > {ws_repo}/.swebench_initial_commit
echo "Created reference commit: $(cat {ws_repo}/.swebench_initial_commit)"
"""


def get_final_diff(container: Container) -> str:
    git_script = r"""#!/usr/bin/env bash
set -euo pipefail

# Read the saved initial commit (survives bashrc reloads)
if [[ ! -f .swebench_initial_commit ]]; then
    echo "ERROR: No initial commit found. Was bootstrap run?"
    exit 1
fi

INITIAL_COMMIT=$(cat .swebench_initial_commit)

# Show a clean diff of all changes since bootstrap
git add -A
git --no-pager diff --cached $INITIAL_COMMIT --stat
echo ""
git --no-pager diff --cached $INITIAL_COMMIT
"""

    try:
        exit_code, output = run_script_in_container(container, git_script)
        if exit_code != 0:
            return f"Git diff failed with exit code {exit_code}: {output}"
        return output
    except Exception as e:
        return f"Failed to get git diff: {str(e)}"


def create_container(
    instance: SWEBenchVerifiedInstance,
    run_id: str = "local",
    client: docker.DockerClient | None = None,
) -> Container:
    if client is None:
        client = docker.from_env()

    spec = make_test_spec(instance=instance.model_dump())
    image_name = spec.instance_image_key
    logger.info(f"Using image {image_name}")

    try:
        client.images.get(image_name)
        logger.info("Image already cached – skipping build.")
    except ImageNotFound:
        logger.info("Image missing – building now (one-time).")
        build_instance_images(dataset=[spec], client=client)

    container_name = f"sweb.eval.{instance.instance_id}.{run_id}"
    try:
        stale = client.containers.get(container_name)
        logger.info(f"Removing pre-existing container {container_name}")
        stale.stop(timeout=5)
        stale.remove(force=True)
    except DockerNotFound:
        pass

    container = build_container(
        test_spec=spec,
        client=client,
        run_id=run_id,
        logger=logger,
        nocache=False,
        force_rebuild=False,
    )

    container.start()
    logger.info("Container started")

    exit_code, output = run_script_in_container(container, apply_patch_script(), conda_neutral=True)
    if exit_code:
        raise RuntimeError(f"apply_patch failed (exit={exit_code})\n{output}")
    logger.info(f"apply_patch phase finished successfully: {output}")

    exit_code, output = run_script_in_container(container, bootstrap_script(instance=instance))
    logger.info(f"Runner finished (exit={exit_code})\n{output}")

    return container


def cleanup_container(container: Container) -> None:
    try:
        container.stop(timeout=5)
        container.remove(force=True)
    except Exception as exc:
        logger.warning(f"Container cleanup failed for {container.name}: {exc}")

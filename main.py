import argparse
import uuid

from rubberduck.autogen.leader_executor.agents.executor import ExecutorAgent
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor
from rubberduck.autogen.leader_executor.utils.dataset_utils import DatasetUtils
from rubberduck.autogen.leader_executor.utils.logger import setup_logger
from rubberduck.autogen.leader_executor.utils.repo_cloner import RepoCloner

SETUP_TASK = """
Initialize the runtime by probing the entire environment—including the helpers directory—and
automatically repair or replace any missing or out-of-range tools.

Required checklist (install / verify each):

  • python                      – record interpreter version (python --version)
  • ripgrep                     – fast file-search utility
  • importlib-metadata          – std-lib back-port needed on Python < 3.8
  • helpers/ast_helper.py ensure_deps
      – run:  python helpers/ast_helper.py --ensure-deps
        (installs astunparse, pyflakes, and any other pinned wheels)

After completing the checklist, output one compact **status report** that lists
*every* verified component and its version in the format:

<component-1>: <version>
<component-2>: <version>
...

The report must contain only this list followed by TERMINATE; add nothing else.Make sure to follow all the
instructions carefully.
"""

PROBLEM_STATEMET = """
### 🛠  Task — **“Mini AST Workout”**

> **Goal:** show that the agent’s AST helper can
>
> 1. **insert** new code,
> 2. **rename** an identifier within a file, and
> 3. **modify** a literal inside a function-call argument—
>    all while keeping the repo syntactically sound.

---

#### 1 · Add a helper function

File: `pylint/__init__.py`  (create it if missing)

Insert **immediately after imports** —or at top if there are none:

```python
def _ast_test_ping() -> str:
    "Return a static string confirming AST edits ran."
    return "pong"
```

---

#### 2 · Rename a constant inside one module

1. Locate the **first** file whose name starts with `format` in the `pylint/` tree
   (e.g. `pylint/format.py`, `pylint/checkers/format.py`, etc.).
2. If that file already defines `DEFAULT_INDENT_SIZE`, **rename** it to
   `DEFAULT_TAB_SIZE` and update every reference *inside that same file only*.
3. If the constant is absent, just inject

```python
DEFAULT_TAB_SIZE: int = 4
```

at module level.

---

#### 3 · Change a literal in a function call

Search that same file for any call like `json.dumps(..., indent=4 …)`.

* If found, change the keyword argument to `indent=2`.
* If none exist, append:

```python
def _ast_json_sanity() -> str:
    import json
    return json.dumps({}, indent=2)
```

---

### ✅ Acceptance checklist

| Check                | Condition                                                |
| -------------------- | -------------------------------------------------------- |
| **Repo parses**      | `python -m py_compile $(git ls-files '*.py')` passes     |
| **Ping present**     | The string `"pong"` appears **once** in the repo         |
| **Constant renamed** | `DEFAULT_INDENT_SIZE` is gone; `DEFAULT_TAB_SIZE` exists |
| **Indent updated**   | At least one `json.dumps(` call uses `indent=2`          |
"""


def main(instance_id: str, logger):
    instance = DatasetUtils.load_instance(instance_id)
    logger.info(f"Loaded instance {instance_id} for repository {instance.repo}")

    repo_executor = RepoDockerExecutor(instance=instance)
    logger.info(f"Initialized Docker executor for repository {instance.repo}")

    repo_cloner = RepoCloner(repo_executor)
    repo_cloner.clone(instance)
    logger.info(f"Cloned repository {instance.repo}")

    executor_agent_setup = ExecutorAgent(repo_executor=repo_executor, instance=instance)
    executor_agent = ExecutorAgent(repo_executor=repo_executor, instance=instance)
    logger.info(f"Initialized ExecutorAgent for {instance.repo}")

    # leader_agent = LeaderAgent(executor_agent=executor_agent, instance=instance)
    logger.info(f"Initialized LeaderAgent for {instance.repo}")

    # resolution = leader_agent.solve_issue(instance.problem_statement)

    setup_report = executor_agent_setup.perform_task(SETUP_TASK)

    task = f"""
# 1. Environment Summary
{setup_report}

# 2. Problem Statement
{instance.problem_statement}
"""

    resolution = executor_agent.perform_task(task)

    logger.info(f"Correct solution: {instance.model_dump_json(indent=2)}")
    return resolution


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leader-Executor agent system runner")
    parser.add_argument("instance_id", type=str, help="Instance ID to process")

    args = parser.parse_args()

    run_id = str(uuid.uuid4())
    logger, log_path = setup_logger(run_id=run_id)
    logger.info("Starting Leader-Executor agent system...")

    main(args.instance_id, logger)
    logger.info(f"Completed processing for {args.instance_id}")

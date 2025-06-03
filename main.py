import argparse
import uuid

from rubberduck.autogen.leader_executor.agents.executor import ExecutorAgent
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor
from rubberduck.autogen.leader_executor.utils.dataset_utils import DatasetUtils
from rubberduck.autogen.leader_executor.utils.logger import setup_logger
from rubberduck.autogen.leader_executor.utils.repo_cloner import RepoCloner

SETUP_TASK = """
Initialize the runtime by probing the entire environment—and automatically install or repair any missing tools.

* **Checklist (perform in this exact order)**

  1. **python**
     * Probe `python --version`
     * No installation ever needed; just record the version string.
  2. **ripgrep**
     * Probe `rg --version`
     * If the probe fails, install with
       ```bash
       apt-get -qq update && apt-get -qq install -y ripgrep
       ```
  3. **ast-grep CLI**
     * Probe `ast-grep --version`
     * Install / upgrade **if** the command is missing **or** the version is lower than `0.37`.
       Try each command in sequence; stop after the first one that succeeds.
       ```bash
       pip install --quiet --upgrade ast-grep-cli
       ```
  4. **ast_grep_rules directory**
     * Probe `test -d /workspace/ast_grep_rules`
     * If absent, create it:
       ```bash
       mkdir -p /workspace/ast_grep_rules
       ```

After completing the checklist, output one compact **status report** listing every
verified component and its version in the format:

<component-1>: <version>
<component-2>: <version>
...

After validating all the items are completed. Generate report must contain only the above list followed by TERMINATE;
add nothing else. Make sure to follow all the instructions carefully.
"""


def main(instance_id: str, logger):
    instance = DatasetUtils.load_instance(instance_id)
    logger.info(f"Loaded instance {instance_id} for repository {instance.repo}")

    repo_executor = RepoDockerExecutor(instance=instance)
    logger.info(f"Initialized Docker executor for repository {instance.repo}")

    repo_cloner = RepoCloner(repo_executor)
    repo_cloner.clone(instance)
    logger.info(f"Cloned repository {instance.repo}")

    executor_agent_setup = ExecutorAgent(
        repo_executor=repo_executor, instance=instance, model_config="gpt-4.1-2025-04-14"
    )
    executor_agent = ExecutorAgent(repo_executor=repo_executor, instance=instance, model_config="gpt-4.1-2025-04-14")
    logger.info(f"Initialized ExecutorAgent for {instance.repo}")

    # leader_agent = LeaderAgent(executor_agent=executor_agent, instance=instance, model_config="gpt-4.1")
    logger.info(f"Initialized LeaderAgent for {instance.repo}")

    # resolution = leader_agent.solve_issue(instance.problem_statement)

    setup_report = executor_agent_setup.perform_task(SETUP_TASK)

    task = f"""
# 1. Environment Summary
{setup_report}

# 2. Problem Statement
{instance.problem_statement}

# 3. Test Requirements
**FAIL_TO_PASS** (must turn green):
{chr(10).join(f'- {test}' for test in instance.fail_to_pass)}

**PASS_TO_PASS** (must stay green):
{chr(10).join(f'- {test}' for test in instance.pass_to_pass)}
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

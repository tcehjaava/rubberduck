import argparse
import uuid

from rubberduck.autogen.leader_executor.agents.executor import ExecutorAgent
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor
from rubberduck.autogen.leader_executor.utils.dataset_utils import DatasetUtils
from rubberduck.autogen.leader_executor.utils.logger import setup_logger
from rubberduck.autogen.leader_executor.utils.repo_cloner import RepoCloner


def main(instance_id: str, logger):
    instance = DatasetUtils.load_instance(instance_id)
    logger.info(f"Loaded instance {instance_id} for repository {instance.repo}")

    repo_executor = RepoDockerExecutor(instance=instance)
    logger.info(f"Initialized Docker executor for repository {instance.repo}")

    repo_cloner = RepoCloner(repo_executor)
    repo_cloner.clone(instance)
    logger.info(f"Cloned repository {instance.repo}")

    executor_agent = ExecutorAgent(repo_executor=repo_executor, instance=instance)
    logger.info(f"Initialized ExecutorAgent for {instance.repo}")

    # leader_agent = LeaderAgent(executor_agent=executor_agent, instance=instance)
    logger.info(f"Initialized LeaderAgent for {instance.repo}")

    # resolution = leader_agent.solve_issue(instance.problem_statement)

    # resolution = executor_agent.perform_task(
    #         """Your task is to collect all setup details—repository name, commit hash, mount path, branch name,
    # project purpose, build steps, test steps, version numbers, and any other facts an autonomous agent would need.
    # Write everything in a file called **Context.md** in the repository’s root directory.
    # """
    #     )
    resolution = executor_agent.perform_task(instance.problem_statement)
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

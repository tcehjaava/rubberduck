import argparse
import uuid
from typing import Iterable, List

from rubberduck.autogen.leader_executor.agents.executor import ExecutorAgent
from rubberduck.autogen.leader_executor.agents.leader import LeaderAgent
from rubberduck.autogen.leader_executor.models.leader import LeaderReviewResponse
from rubberduck.autogen.leader_executor.prompts import load_markdown_message
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor
from rubberduck.autogen.leader_executor.utils.dataset_utils import DatasetUtils
from rubberduck.autogen.leader_executor.utils.json_extract import parse_leader_response
from rubberduck.autogen.leader_executor.utils.logger import setup_logger
from rubberduck.autogen.leader_executor.utils.repo_cloner import RepoCloner


def build_previous_context(feedbacks: Iterable[str]) -> str:
    feedbacks = list(feedbacks)
    if not feedbacks:
        return "This is the first iteration. No feedback."

    lines: List[str] = ["=== Previous Feedbacks from Leader ==="]
    for i, feedback in enumerate(feedbacks, 1):
        lines.append(f"=== Feedback of attempt {i}: ===")
        lines.append(feedback)

    return "\n".join(lines)


def format_chat_history(chat_result) -> str:
    if not chat_result or not hasattr(chat_result, "chat_history"):
        return "No conversation history available."

    chat_history = chat_result.chat_history
    if not chat_history:
        return "No conversation history available."

    formatted_lines = []

    for i, message in enumerate(chat_history):
        role = message.get("role", "unknown")
        name = message.get("name", role)
        content = message.get("content", "")

        formatted_lines.append(f"=== Message {i+1}: {name.upper()} ===")
        formatted_lines.append(content)
        formatted_lines.append("")

    return "\n".join(formatted_lines)


def extract_leader_feedback(leader_response: LeaderReviewResponse) -> str:
    feedback_sections = []

    if leader_response.what_executor_did_well:
        feedback_sections.append(
            "**What you did well:**\n" + "\n".join(f"- {item}" for item in leader_response.what_executor_did_well)
        )

    if leader_response.what_executor_did_poorly:
        feedback_sections.append(
            "**What to improve:**\n" + "\n".join(f"- {item}" for item in leader_response.what_executor_did_poorly)
        )

    if leader_response.recommendations_for_next_run:
        feedback_sections.append(
            "**Recommendations for this run:**\n"
            + "\n".join(f"- {item}" for item in leader_response.recommendations_for_next_run)
        )

    if leader_response.reasoning:
        feedback_sections.append(f"**Analysis:**\n{leader_response.reasoning}")

    return "\n\n".join(feedback_sections)


def main(instance_id: str, logger):
    instance = DatasetUtils.load_instance(instance_id)
    logger.info(f"Loaded instance {instance_id} for repository {instance.repo}")

    repo_executor = RepoDockerExecutor(instance=instance)
    logger.info(f"Initialized Docker executor for repository {instance.repo}")

    repo_cloner = RepoCloner(repo_executor)

    executor_agent = ExecutorAgent(repo_executor=repo_executor, instance=instance, model_config="gpt-4.1-2025-04-14")
    leader_agent = LeaderAgent(executor_agent=executor_agent, instance=instance, model_config="o3-2025-04-16")
    logger.info(f"Initialized ExecutorAgent and LeaderAgent for {instance.repo}")

    max_iterations = 3
    previous_feedbacks = []

    for iteration in range(1, max_iterations + 1):
        logger.info(f"Starting iteration {iteration}/{max_iterations}")

        logger.info("Resetting repository to clean state...")
        repo_cloner.clone(instance)
        logger.info(f"Cloned repository {instance.repo}")

        setup_chat = executor_agent.perform_task(load_markdown_message("setup_task.md"))
        logger.info("Completed environment setup")

        previous_context = build_previous_context(previous_feedbacks)

        executor_task = load_markdown_message(
            "executor_task.md",
            iteration=iteration,
            max_iterations=max_iterations,
            setup_report=getattr(setup_chat, "summary", "No setup result available."),
            problem_statement=instance.problem_statement,
            fail_to_pass_tests="\n".join(f"- {test}" for test in instance.fail_to_pass),
            pass_to_pass_tests="\n".join(f"- {test}" for test in instance.pass_to_pass),
            previous_context=previous_context,
        )

        logger.info(f"Executing task for iteration {iteration}")
        executor_result = executor_agent.perform_task(executor_task)

        leader_task = load_markdown_message(
            "leader_task.md",
            iteration=iteration,
            max_iterations=max_iterations,
            executor_messages=format_chat_history(executor_result),
        )

        logger.info(f"Sending results to leader for review (iteration {iteration})")
        leader_chat = leader_agent.solve_issue(leader_task)
        leader_response = parse_leader_response(leader_chat)

        if leader_response.decision == "SOLVED":
            logger.info(f"Leader determined success after iteration {iteration}")
            break
        elif iteration == max_iterations:
            logger.info(f"Maximum iterations reached after iteration {iteration}")
            break
        else:
            logger.info(f"Leader decided to retry after iteration {iteration}")

            current_feedback = extract_leader_feedback(leader_response)
            previous_feedbacks.append(current_feedback)

    logger.info(f"Correct solution: {instance.model_dump_json(indent=2)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leader-Executor agent system runner")
    parser.add_argument("instance_id", type=str, help="Instance ID to process")

    args = parser.parse_args()

    run_id = str(uuid.uuid4())
    logger, log_path = setup_logger(run_id=run_id)
    logger.info("Starting Leader-Executor agent system...")

    main(args.instance_id, logger)
    logger.info(f"Completed processing for {args.instance_id}")

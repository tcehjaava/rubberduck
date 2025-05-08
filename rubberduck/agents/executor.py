import logging

from autogen import AssistantAgent, UserProxyAgent

from rubberduck.autogen.leader_executor.config import load_llm_config
from rubberduck.autogen.leader_executor.tools import RepoDockerExecutor

logger = logging.getLogger(__name__)

TERMINATION_MESSAGE = "TERMINATE"

EXECUTOR_SYSTEM_MESSAGE = f"""
You are **Rubberduck Executor**, an autonomous coding agent that carries out
atomic actions produced by a Leader agent.

══════════  Context  ══════════
• You operate inside a Linux container with shell access provided by the driver
  (code blocks tagged ```bash``` or ```sh``` are executed automatically).
• The repository has already been cloned to **/workspace** (a writable
  working directory).  
• No human is in the loop: the Leader is your only interlocutor and will not
  answer questions.

══════════  Task Loop  ══════════
1. Read the Leader’s instruction.
2. Decide whether the action needs shell commands or file edits.
3. Emit **one** code block that completes the action **fully**.
4. Analyse the execution result that the driver returns.
   • If the task is finished, explain the outcome briefly, then output the
     single word **{TERMINATION_MESSAGE}**.
   • If an error occurs, rethink, emit a *new complete* code block, and try
     again (max 2 retries).  
5. Never ask the Leader or a user for additional information.

══════════  Code-generation rules  ══════════
• Only one code block per response; prefix `# filename: <name>` when a file
  must be created/overwritten.  
• Use `print` to surface results instead of asking the user to copy/paste.  
• Avoid destructive commands (`rm -rf /`, `shutdown`, etc.).  
• Do not install new packages unless absolutely required; justify if you do.  
• Keep commands idempotent so reruns do not corrupt state.

══════════  Termination  ══════════
When the requested action (or best-effort recovery) is complete, respond with
exactly **{TERMINATION_MESSAGE}**—no additional text, punctuation, or code.
"""

EXECUTOR_DESCRIPTION = (
    "Autonomous Executor for Rubberduck: executes shell commands and file "
    "edits in /workspace on behalf of the Leader, streams results, and ends "
    f"each task with the literal word '{TERMINATION_MESSAGE}'."
)


def is_termination_msg(msg: dict) -> bool:
    return msg.get("content", "").rstrip().endswith(TERMINATION_MESSAGE)


class ExecutorAgent:
    def __init__(self, repo_executor: RepoDockerExecutor, model_config: str = "default_executor"):
        self._repo_executor: RepoDockerExecutor = repo_executor
        config_list = load_llm_config(model_config)

        self.executor = AssistantAgent(
            name="EXECUTOR",
            system_message=EXECUTOR_SYSTEM_MESSAGE,
            description=EXECUTOR_DESCRIPTION,
            llm_config={"config_list": config_list, "temperature": 0},
            is_termination_msg=is_termination_msg,
            human_input_mode="NEVER",
        )

        self.proxy = UserProxyAgent(
            name="DRIVER",
            human_input_mode="NEVER",
            code_execution_config={
                "executor": self._repo_executor,
            },
            llm_config=False,
            is_termination_msg=is_termination_msg,
        )

    def perform_task(self, task: str) -> None:
        logger.info("ExecutorAgent received task: %s", task)
        self.proxy.initiate_chat(self.executor, message=task)

import atexit
import copy
from contextlib import ExitStack
from typing import Any, Dict, Union

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph
from loguru import logger

from rubberduck.autogen.leader_executor.agents.autonomous import AutonomousAgent
from rubberduck.autogen.leader_executor.models.autonomous_config import (
    AutonomousAgentConfig,
)
from rubberduck.autogen.leader_executor.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)
from rubberduck.autogen.leader_executor.models.swebench_workflow import (
    SWEBenchWorkflowConfig,
    SWEBenchWorkflowNode,
    SWEBenchWorkflowState,
)
from rubberduck.autogen.leader_executor.prompts import load_markdown_message
from rubberduck.autogen.leader_executor.tools.docker_executor import RepoDockerExecutor
from rubberduck.autogen.leader_executor.utils.dataset_utils import DatasetUtils
from rubberduck.autogen.leader_executor.utils.helpers import (
    build_previous_context,
    format_chat_history,
    format_content_with_indent,
)
from rubberduck.autogen.leader_executor.utils.logger import (
    dump_single_entry,
    get_log_dir,
)
from rubberduck.autogen.leader_executor.utils.repo_cloner import RepoCloner


class BundleContainer:
    def __init__(self, docker, leader_agent, executor_agent, leader_should_continue_agent):
        self.docker = docker
        self.leader_agent = leader_agent
        self.executor_agent = executor_agent
        self.leader_should_continue_agent = leader_should_continue_agent


_REG: Dict[str, BundleContainer] = {}
_EXIT_STACKS: dict[str, ExitStack] = {}


def ensure_bundle(
    thread_id: str,
    instance: SWEBenchVerifiedInstance,
    model_leader: str | None = None,
    model_exec: str | None = None,
) -> BundleContainer:
    if thread_id in _REG:
        return _REG[thread_id]

    stack = ExitStack()
    _EXIT_STACKS[thread_id] = stack

    assert model_leader is not None, "model_leader must not be None"
    assert model_exec is not None, "model_exec must not be None"

    docker_exec = RepoDockerExecutor(instance)
    stack.callback(docker_exec.stop)

    executor_system_prompt = load_markdown_message("executor.md", repo_name=instance.repo_subdir_name)

    executor_agent = AutonomousAgent(
        AutonomousAgentConfig(
            assistant_name=SWEBenchWorkflowNode.EXECUTOR.value.upper(),
            proxy_name=f"{SWEBenchWorkflowNode.EXECUTOR.value.upper()}_PROXY",
            system_message=executor_system_prompt,
            model_config=model_exec,
            temperature=0,
            code_execution_config={"executor": docker_exec},
            max_turns=100,
        )
    )

    leader_agent = AutonomousAgent(
        AutonomousAgentConfig(
            assistant_name=SWEBenchWorkflowNode.LEADER.value.upper(),
            proxy_name=f"{SWEBenchWorkflowNode.LEADER.value.upper()}_PROXY",
            system_message=load_markdown_message("leader.md", executor_system_prompt=executor_system_prompt),
            model_config=model_leader,
            temperature=0,
            max_turns=5,
        )
    )

    leader_should_continue_agent = AutonomousAgent(
        AutonomousAgentConfig(
            assistant_name=SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE.value.upper(),
            proxy_name=f"{SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE.value.upper()}_PROXY",
            system_message=load_markdown_message("leader_should_continue.md"),
            model_config=model_exec,
            temperature=0,
            max_turns=5,
        )
    )

    bundle = BundleContainer(docker_exec, leader_agent, executor_agent, leader_should_continue_agent)
    _REG[thread_id] = bundle
    return bundle


def _close_all_bundles():
    for tid, stack in list(_EXIT_STACKS.items()):
        stack.close()
        _EXIT_STACKS.pop(tid, None)
        _REG.pop(tid, None)


def close_bundle(thread_id: str):
    stack = _EXIT_STACKS.pop(thread_id, None)
    if stack:
        stack.close()
    _REG.pop(thread_id, None)


atexit.register(_close_all_bundles)

_MAX_ATTEMPTS = 3

_SKIP_NODES: set[SWEBenchWorkflowNode] = {
    SWEBenchWorkflowNode.INIT,
    SWEBenchWorkflowNode.REPO_CLONE,
    SWEBenchWorkflowNode.CLEANUP,
}


class SWEBenchWorkflow:
    def __init__(self):
        _checkpointer_cm = PostgresSaver.from_conn_string("postgresql://postgres:postgres@localhost:5432/postgres")
        self.checkpointer = _checkpointer_cm.__enter__()
        self.checkpointer.setup()
        atexit.register(_checkpointer_cm.__exit__, None, None, None)

        self.workflow = self._build_workflow()

    @staticmethod
    def _update_memory(
        state: SWEBenchWorkflowState, result: Any, node_key: Union[str, SWEBenchWorkflowNode]
    ) -> Dict[str, Any]:
        key = node_key if isinstance(node_key, str) else node_key.value
        mem = {**state.get("memory", {})}
        mem.setdefault(key, []).append(copy.deepcopy(result))

        if node_key not in _SKIP_NODES:
            dump_single_entry(key, mem[key][-1], len(mem[key]), get_log_dir())
        return mem

    @staticmethod
    def _handle_node_exception(
        state: SWEBenchWorkflowState, exc: Exception, node_key: Union[str, SWEBenchWorkflowNode]
    ) -> SWEBenchWorkflowState:
        name = node_key if isinstance(node_key, str) else node_key.value
        logger.exception(f"{name.title()} failed")
        return {**state, "result": None, "error_message": str(exc)}

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(SWEBenchWorkflowState, config_schema=SWEBenchWorkflowConfig)

        workflow.add_node(SWEBenchWorkflowNode.INIT.value, self._init_node)
        workflow.add_node(SWEBenchWorkflowNode.REPO_CLONE.value, self._repo_clone_node)
        workflow.add_node(SWEBenchWorkflowNode.SETUP.value, self._setup_node)
        workflow.add_node(SWEBenchWorkflowNode.EXECUTOR.value, self._executor_node)
        workflow.add_node(SWEBenchWorkflowNode.LEADER.value, self._leader_node)
        workflow.add_node(SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE.value, self._leader_should_continue_node)
        workflow.add_node(SWEBenchWorkflowNode.CLEANUP.value, self._cleanup_node)

        workflow.add_conditional_edges(
            SWEBenchWorkflowNode.INIT.value,
            self._should_continue,
            {"continue": SWEBenchWorkflowNode.REPO_CLONE.value, "complete": SWEBenchWorkflowNode.CLEANUP.value},
        )

        workflow.add_conditional_edges(
            SWEBenchWorkflowNode.REPO_CLONE.value,
            self._should_continue,
            {"continue": SWEBenchWorkflowNode.SETUP.value, "complete": SWEBenchWorkflowNode.CLEANUP.value},
        )

        workflow.add_conditional_edges(
            SWEBenchWorkflowNode.SETUP.value,
            self._should_continue,
            {"continue": SWEBenchWorkflowNode.EXECUTOR.value, "complete": SWEBenchWorkflowNode.CLEANUP.value},
        )

        workflow.add_conditional_edges(
            SWEBenchWorkflowNode.EXECUTOR.value,
            self._should_continue,
            {"continue": SWEBenchWorkflowNode.LEADER.value, "complete": SWEBenchWorkflowNode.CLEANUP.value},
        )

        workflow.add_conditional_edges(
            SWEBenchWorkflowNode.LEADER.value,
            self._should_continue,
            {
                "continue": SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE.value,
                "complete": SWEBenchWorkflowNode.CLEANUP.value,
            },
        )

        workflow.add_conditional_edges(
            SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE.value,
            self._should_leader_continue,
            {
                "continue": SWEBenchWorkflowNode.REPO_CLONE.value,
                "complete": SWEBenchWorkflowNode.CLEANUP.value,
            },
        )

        workflow.add_edge(SWEBenchWorkflowNode.CLEANUP.value, END)

        workflow.set_entry_point(SWEBenchWorkflowNode.INIT.value)

        return workflow.compile(checkpointer=self.checkpointer)

    def _init_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        tid = config["configurable"]["thread_id"]
        instance_id = config["configurable"]["instance_id"]
        logger.info(f"INIT – loading instance {instance_id}")

        try:
            instance = DatasetUtils.load_instance(instance_id)
            ensure_bundle(tid, instance, "claude-3-7-sonnet-latest", "gpt-4.1-2025-04-14")
            logger.info("INIT – heavy objects created")

            memory = {**state.get("memory", {})}
            if "leader_feedback" not in memory:
                memory["leader_feedback"] = []

            return {
                **state,
                "current_attempt": state.get("current_attempt", 1),
                "max_attempts": state.get("max_attempts", _MAX_ATTEMPTS),
                "instance": instance,
                "result": "Initialization complete",
                "error_message": "",
                "memory": self._update_memory({"memory": memory}, "initialised", SWEBenchWorkflowNode.INIT),
            }
        except Exception as e:
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.INIT)

    def _repo_clone_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        try:
            tid = config["configurable"]["thread_id"]
            bundle = ensure_bundle(tid, state["instance"])

            logger.info(f"Cloning repository for attempt {state['current_attempt']}/{state['max_attempts']}")

            instance = state["instance"]
            docker_executor = bundle.docker

            repo_cloner = RepoCloner(docker_executor)
            repo_cloner.clone(instance)

            logger.info(f"Successfully cloned repository {instance.repo}")

            return {
                **state,
                "result": "Repository cloned successfully",
                "error_message": "",
                "memory": self._update_memory(state, "Repository cloned", SWEBenchWorkflowNode.REPO_CLONE),
            }

        except Exception as e:
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.REPO_CLONE)

    def _setup_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        try:
            tid = config["configurable"]["thread_id"]
            bundle = ensure_bundle(tid, state["instance"])

            logger.info(f"Setting up environment for attempt {state['current_attempt']}")
            setup_result = bundle.executor_agent.execute_task(load_markdown_message("setup_task.md"))
            logger.info("Completed environment setup")

            return {
                **state,
                "result": setup_result,
                "error_message": "",
                "memory": self._update_memory(state, setup_result, SWEBenchWorkflowNode.SETUP),
            }

        except Exception as e:
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.SETUP)

    def _executor_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        logger.info(f"Executor attempt {state['current_attempt']}/{state['max_attempts']}")

        try:
            tid = config["configurable"]["thread_id"]
            bundle = ensure_bundle(tid, state["instance"])

            previous_context = build_previous_context(state["memory"]["leader_feedback"])

            result = bundle.executor_agent.execute_task(
                load_markdown_message(
                    "executor_task.md",
                    iteration=state["current_attempt"],
                    max_iterations=state["max_attempts"],
                    setup_report=format_content_with_indent(
                        getattr(state.get("result"), "summary", "No setup result available.")
                    ),
                    problem_statement=format_content_with_indent(state["instance"].problem_statement),
                    previous_context=format_content_with_indent(previous_context),
                )
            )

            return {
                **state,
                "result": result,
                "error_message": "",
                "memory": self._update_memory(state, result, SWEBenchWorkflowNode.EXECUTOR),
            }

        except Exception as e:
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.EXECUTOR)

    def _leader_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        logger.info(f"Leader reviewing attempt {state['current_attempt']}")

        try:
            tid = config["configurable"]["thread_id"]
            bundle = ensure_bundle(tid, state["instance"])

            result = bundle.leader_agent.execute_task(
                load_markdown_message("leader_task.md", executor_messages=format_chat_history(state["result"]))
            )

            updated_memory = self._update_memory(state, result, SWEBenchWorkflowNode.LEADER)
            updated_memory["leader_feedback"].append(getattr(result, "summary", "No leader response."))

            return {
                **state,
                "result": result,
                "error_message": "",
                "memory": updated_memory,
            }

        except Exception as e:
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.LEADER)

    def _leader_should_continue_node(
        self, state: SWEBenchWorkflowState, *, config: RunnableConfig
    ) -> SWEBenchWorkflowState:
        try:
            tid = config["configurable"]["thread_id"]
            bundle = ensure_bundle(tid, state["instance"])

            result = bundle.leader_should_continue_agent.execute_task(state["memory"]["leader_feedback"][-1])

            return {
                **state,
                "result": result,
                "error_message": "",
                "current_attempt": state["current_attempt"] + 1,
                "memory": self._update_memory(state, result, SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE),
            }

        except Exception as e:
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE)

    def _cleanup_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        close_bundle(config["configurable"]["thread_id"])
        return state

    @staticmethod
    def _should_continue(state: SWEBenchWorkflowState) -> str:
        return "complete" if state.get("error_message") else "continue"

    @staticmethod
    def _should_leader_continue(state: SWEBenchWorkflowState) -> str:
        if state.get("error_message"):
            return "complete"
        if state.get("result") and "solved" in str(state["result"]).lower():
            return "complete"
        if state["current_attempt"] > state["max_attempts"]:
            return "complete"
        return "continue"

    def run(self, instance_id: str, thread_id: str) -> Dict[str, Any]:
        logger.info(f"Starting SWEBenchWorkflow with thread_id: {thread_id}")
        final = self.workflow.invoke(
            {},
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "instance_id": instance_id,
                }
            },
        )
        return final


def get_graph(_: Dict[str, Any] | None = None):
    return SWEBenchWorkflow().workflow

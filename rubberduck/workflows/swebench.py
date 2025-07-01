import atexit
import copy
from contextlib import ExitStack
from typing import Any, Dict, Union

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph
from loguru import logger

from rubberduck.agents.autonomous import AutonomousAgent
from rubberduck.models.autonomous_config import (
    AutonomousAgentConfig,
)
from rubberduck.models.semantic_search_config import SemanticSearchConfig
from rubberduck.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)
from rubberduck.models.swebench_workflow import (
    SWEBenchWorkflowConfig,
    SWEBenchWorkflowNode,
    SWEBenchWorkflowState,
)
from rubberduck.prompts import load_markdown_message
from rubberduck.tools.container_manager import (
    cleanup_container,
    create_container,
    get_final_diff,
)
from rubberduck.tools.semantic_search import SemanticSearch
from rubberduck.utils.dataset_utils import DatasetUtils
from rubberduck.utils.logger import (
    dump_single_entry,
    get_log_dir,
)
from rubberduck.utils.message_helpers import (
    build_all_iteration_logs,
    build_previous_context,
    format_chat_history,
    format_content_with_indent,
)


class BundleContainer:
    def __init__(self, docker_runner, leader_agent, executor_agent, logger_agent, leader_should_continue_agent):
        self.docker_runner = docker_runner
        self.leader_agent = leader_agent
        self.executor_agent = executor_agent
        self.logger_agent = logger_agent
        self.leader_should_continue_agent = leader_should_continue_agent


_REG: Dict[str, BundleContainer] = {}
_EXIT_STACKS: dict[str, ExitStack] = {}


_MAX_ATTEMPTS = 15
_EXECUTOR_MAX_TURNS = 100
_LEADER_MAX_TURNS = 1


def ensure_bundle(
    thread_id: str,
    instance: SWEBenchVerifiedInstance | None = None,
    model_leader: str | None = None,
    model_exec: str | None = None,
) -> BundleContainer:
    if thread_id in _REG:
        return _REG[thread_id]

    stack = ExitStack()
    _EXIT_STACKS[thread_id] = stack

    assert instance is not None, "instance must not be None"
    assert model_leader is not None, "model_leader must not be None"
    assert model_exec is not None, "model_exec must not be None"

    docker_runner = create_container(instance)
    stack.callback(lambda: cleanup_container(docker_runner))

    # sleep(100000)

    semantic_search = SemanticSearch(
        config=SemanticSearchConfig(), instance_id=instance.instance_id, container=docker_runner
    )
    semantic_search.index_codebase()

    executor_system_prompt = load_markdown_message("executor.md")

    executor_agent = AutonomousAgent(
        AutonomousAgentConfig(
            assistant_name=SWEBenchWorkflowNode.EXECUTOR.value.upper(),
            proxy_name=f"{SWEBenchWorkflowNode.EXECUTOR.value.upper()}_PROXY",
            system_message=executor_system_prompt,
            model_config=model_exec,
            docker_runner=docker_runner,
            semantic_search=semantic_search,
            max_turns=_EXECUTOR_MAX_TURNS,
        )
    )

    leader_agent = AutonomousAgent(
        AutonomousAgentConfig(
            assistant_name=SWEBenchWorkflowNode.LEADER.value.upper(),
            proxy_name=f"{SWEBenchWorkflowNode.LEADER.value.upper()}_PROXY",
            system_message=load_markdown_message("leader.md", executor_system_prompt=executor_system_prompt),
            model_config=model_leader,
            max_turns=_LEADER_MAX_TURNS,
        )
    )

    logger_agent = AutonomousAgent(
        AutonomousAgentConfig(
            assistant_name=SWEBenchWorkflowNode.LOGGER.value.upper(),
            proxy_name=f"{SWEBenchWorkflowNode.LOGGER.value.upper()}_PROXY",
            system_message=load_markdown_message("log_extractor.md", executor_system_prompt=executor_system_prompt),
            model_config="o3-2025-04-16",
            max_turns=_LEADER_MAX_TURNS,
        )
    )

    leader_should_continue_agent = AutonomousAgent(
        AutonomousAgentConfig(
            assistant_name=SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE.value.upper(),
            proxy_name=f"{SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE.value.upper()}_PROXY",
            system_message=load_markdown_message("leader_should_continue.md"),
            model_config=model_exec,
            max_turns=_LEADER_MAX_TURNS,
        )
    )

    bundle = BundleContainer(docker_runner, leader_agent, executor_agent, logger_agent, leader_should_continue_agent)
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

_SKIP_NODES: set[SWEBenchWorkflowNode] = {
    SWEBenchWorkflowNode.INIT,
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
        workflow.add_node(SWEBenchWorkflowNode.SETUP.value, self._setup_node)
        workflow.add_node(SWEBenchWorkflowNode.EXECUTOR.value, self._executor_node)
        workflow.add_node(SWEBenchWorkflowNode.LOGGER.value, self._logger_node)
        workflow.add_node(SWEBenchWorkflowNode.LEADER.value, self._leader_node)
        workflow.add_node(SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE.value, self._leader_should_continue_node)
        workflow.add_node(SWEBenchWorkflowNode.CLEANUP.value, self._cleanup_node)

        workflow.add_conditional_edges(
            SWEBenchWorkflowNode.INIT.value,
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
            {"continue": SWEBenchWorkflowNode.LOGGER.value, "complete": SWEBenchWorkflowNode.CLEANUP.value},
        )

        workflow.add_conditional_edges(
            SWEBenchWorkflowNode.LOGGER.value,
            self._should_continue,
            {
                "continue": SWEBenchWorkflowNode.LEADER.value,
                "complete": SWEBenchWorkflowNode.CLEANUP.value,
            },
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
                "continue": SWEBenchWorkflowNode.EXECUTOR.value,
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
            state = self._cleanup_node(state, config=config)

            instance = DatasetUtils.load_instance(instance_id)
            ensure_bundle(tid, instance, "claude-opus-4-20250514", "gpt-4.1-2025-04-14")
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

    def _setup_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        try:
            tid = config["configurable"]["thread_id"]
            bundle = ensure_bundle(tid)

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
            bundle = ensure_bundle(tid)

            previous_context = build_previous_context(
                state["memory"].get("leader_feedback", []), state["memory"].get(SWEBenchWorkflowNode.LOGGER.value, [])
            )

            setup_memory = state["memory"].get(SWEBenchWorkflowNode.SETUP.value, [])
            setup_report = format_content_with_indent(
                getattr(setup_memory[-1], "summary", "No setup report available.")
                if setup_memory
                else "No setup report available."
            )

            git_diff_output = get_final_diff(bundle.docker_runner)

            result = bundle.executor_agent.execute_task(
                load_markdown_message(
                    "executor_task.md",
                    iteration=state["current_attempt"],
                    max_iterations=state["max_attempts"],
                    setup_report=setup_report,
                    problem_statement=format_content_with_indent(state["instance"].problem_statement),
                    previous_context=previous_context,
                    git_diff_output=format_content_with_indent(git_diff_output),
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

    def _logger_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        logger.info(f"Logger extracting technical details from attempt {state['current_attempt']}")

        try:
            tid = config["configurable"]["thread_id"]
            bundle = ensure_bundle(tid)

            executor_memory = state["memory"].get(SWEBenchWorkflowNode.EXECUTOR.value, [])
            assert len(executor_memory) > 0, "Executor doesn't have any memory"

            result = bundle.logger_agent.execute_task(format_chat_history(executor_memory[-1]))

            return {
                **state,
                "result": result,
                "error_message": "",
                "memory": self._update_memory(
                    state, getattr(result, "summary", "No logger response."), SWEBenchWorkflowNode.LOGGER
                ),
            }

        except Exception as e:
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.LOGGER)

    def _leader_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        logger.info(f"Leader reviewing attempt {state['current_attempt']}")

        try:
            tid = config["configurable"]["thread_id"]
            bundle = ensure_bundle(tid)

            all_iteration_logs = build_all_iteration_logs(state["memory"].get(SWEBenchWorkflowNode.LOGGER.value, []))

            executor_memory = state["memory"].get(SWEBenchWorkflowNode.EXECUTOR.value, [])
            assert len(executor_memory) > 0, "Executor doesn't have any memory"

            git_diff_output = get_final_diff(bundle.docker_runner)

            result = bundle.leader_agent.execute_task(
                load_markdown_message(
                    "leader_task.md",
                    problem_statement=format_content_with_indent(state["instance"].problem_statement),
                    executor_messages=format_chat_history(executor_memory[-1]),
                    all_iteration_logs=all_iteration_logs,
                    git_diff_output=format_content_with_indent(git_diff_output),
                )
            )

            updated_memory = self._update_memory(state, result, SWEBenchWorkflowNode.LEADER)
            updated_memory = self._update_memory(
                {"memory": updated_memory}, getattr(result, "summary", "No leader response."), "leader_feedback"
            )

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
            bundle = ensure_bundle(tid)

            result = bundle.leader_should_continue_agent.execute_task(state["memory"]["leader_feedback"][-1])

            return {
                **state,
                "result": getattr(result, "summary", "No leader response."),
                "error_message": "",
                "current_attempt": state["current_attempt"] + 1,
                "memory": self._update_memory(
                    state,
                    getattr(result, "summary", "No leader should continue response."),
                    SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE,
                ),
            }

        except Exception as e:
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.LEADER_SHOULD_CONTINUE)

    def _cleanup_node(self, state: SWEBenchWorkflowState, *, config: RunnableConfig) -> SWEBenchWorkflowState:
        try:
            tid = config["configurable"]["thread_id"]
            bundle = _REG.get(tid)

            if bundle and bundle.docker_runner:
                diff_output = get_final_diff(bundle.docker_runner)

                updated_state = {
                    **state,
                    "result": diff_output,
                    "error_message": "",
                    "memory": self._update_memory(state, diff_output, SWEBenchWorkflowNode.CLEANUP),
                }
            else:
                updated_state = state

            close_bundle(tid)
            logger.info("Workflow completed")
            return updated_state

        except Exception as e:
            close_bundle(config["configurable"]["thread_id"])
            return self._handle_node_exception(state, e, SWEBenchWorkflowNode.CLEANUP)

    @staticmethod
    def _should_continue(state: SWEBenchWorkflowState) -> str:
        return "complete" if state.get("error_message") else "continue"

    @staticmethod
    def _should_leader_continue(state: SWEBenchWorkflowState) -> str:
        if state.get("error_message"):
            logger.info("Error message found, stopping execution.")
            return "complete"
        if state.get("result") and "solved" in str(state["result"]).lower():
            logger.info("Problem solved, stopping execution.")
            return "complete"
        if state.get("result") and "failed" in str(state["result"]).lower():
            logger.info("Problem failed, stopping execution.")
            return "complete"
        if state["current_attempt"] > state["max_attempts"]:
            logger.info(
                f"Max attempts reached, stopping execution: {state['current_attempt']} > {state['max_attempts']}"
            )
            return "complete"
        return "continue"

    def run(self, instance_id: str, thread_id: str) -> Dict[str, Any]:
        logger.info(f"Starting SWEBenchWorkflow with thread_id: {thread_id}")
        final = self.workflow.invoke(
            {},
            config={
                "recursion_limit": 1000,
                "configurable": {
                    "thread_id": thread_id,
                    "instance_id": instance_id,
                },
            },
        )
        return final


def get_graph(_: Dict[str, Any] | None = None):
    return SWEBenchWorkflow().workflow

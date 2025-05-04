import json
import logging
import textwrap
from pathlib import Path

from rubberduck.langgraph.graph_orchestrator.models import WorkflowState


class WorkflowLogger:

    @staticmethod
    def log_all_agents_history(state: WorkflowState, agents_log_dir: Path) -> None:
        separator = "=" * 60

        for agent_name, contexts in state.contexts.items():
            agent_log_file = agents_log_dir / f"{agent_name}.log"

            header = f"Agent Execution History: [{agent_name}]"
            history_entries = []
            iteration_counter = 1

            for context in contexts:
                for record in context.history:
                    entry_header = f"Iteration {iteration_counter}"
                    iteration_counter += 1
                    content = ""

                    if record.prompt:
                        content += f"Prompt:\n{textwrap.indent(record.prompt, '  ')}\n"

                    if record.error:
                        content += f"Error:\n{textwrap.indent(record.error, '  ')}\n\n"

                    if record.raw_result:
                        result_str = json.dumps(record.raw_result, indent=2, ensure_ascii=False)
                        content += f"Result:\n{textwrap.indent(result_str, '  ')}\n"

                    history_entries.append(f"{separator}\n{entry_header}\n{separator}\n{content}")

            full_history = f"{separator}\n{header}\n{separator}\n" + "\n".join(history_entries) + f"\n{separator}\n"

            with agent_log_file.open("w", encoding="utf-8") as log_file:
                log_file.write(full_history)

    @staticmethod
    def print_agent_output(state: WorkflowState, agent_name: str) -> None:
        context = state.get_latest_context(agent_name)
        last_record = context.get_last_record()

        separator = "=" * 60
        header = f"Agent Output: [{agent_name}]"

        if last_record is None:
            content = f"No execution history available for agent '{agent_name}'."
        elif last_record.error:
            content = textwrap.indent(f"Error:\n{last_record.error}", prefix="  ")
        elif last_record.raw_result:
            formatted_output = json.dumps(last_record.raw_result, indent=2, ensure_ascii=False)
            content = textwrap.indent(f"Output:\n{formatted_output}", prefix="  ")
        else:
            content = f"Agent '{agent_name}' produced no output."

        full_message = f"\n{separator}\n{header}\n{separator}\n{content}\n{separator}"

        logging.info(full_message)

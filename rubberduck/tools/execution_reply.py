import time
from typing import Optional

from autogen.code_utils import extract_code
from docker.models.containers import Container
from utils.message_helpers import is_termination_msg

from rubberduck.tools.apply_patch import run_script_in_container
from rubberduck.tools.semantic_search import SemanticSearch

BASH_LANGS = {"bash", "sh", "shell"}


def _split_commands(block: str) -> list[str]:
    if block.lstrip().startswith("```"):
        block = block.split("\n", 1)[1]
    return [block.strip()] if block.strip() else []


def _truncate(text: str, *, max_chars=12000, head=10, tail=10) -> str:
    if len(text) <= max_chars:
        return text

    lines = text.splitlines()

    if len(lines) <= head + tail:
        half = max_chars // 2
        return f"{text[:half]}\n<Message truncated – {len(text)} chars>\n{text[-half:]}"

    snippet = lines[:head] + [f"<Message truncated – {len(lines)} lines>"] + lines[-tail:]
    return "\n".join(snippet)


def truncate(text: str, *, max_chars=12000, head=10, tail=10) -> str:
    return _truncate(text, max_chars=max_chars, head=head, tail=tail)


def create_execution_reply(container: Container, semantic_search: Optional[SemanticSearch] = None):
    def _execution_reply(recipient, messages=None, sender=None, config=None):
        if not messages:
            return False, None
        elif is_termination_msg(messages[-1]):
            return False, None

        time.sleep(3)

        last = messages[-1].get("content") or ""
        code_blocks = extract_code(last)

        if not code_blocks:
            return False, None

        executable_blocks = [
            (lang, code)
            for lang, code in code_blocks
            if lang in BASH_LANGS or (lang == "semantic_search" and semantic_search)
        ]

        if not executable_blocks:
            return False, None

        logs = []

        for lang, code in executable_blocks:
            if lang in BASH_LANGS:
                for cmd in _split_commands(code):
                    exit_code, output = run_script_in_container(container, cmd)
                    logs.append(f"{output}")
                    if exit_code:
                        logs[-1] = f"exit {exit_code}\n{output}"
                        reply = "❌ Bash execution halted on error:\n\n" + "\n".join(logs)
                        return True, _truncate(reply)

            elif lang == "semantic_search" and semantic_search:
                query = code.strip()
                if query:
                    try:
                        search_result = semantic_search.search(query)
                        logs.append(f"🔍 Search: {query}\n\n{search_result}")
                    except Exception as e:
                        logs.append(f"❌ Search failed for '{query}': {str(e)}")

        return True, _truncate("✅ Execution completed:\n\n" + "\n\n".join(logs))

    return _execution_reply

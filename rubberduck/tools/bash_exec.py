from autogen.code_utils import extract_code
from docker.models.containers import Container

from rubberduck.tools.apply_patch import run_script_in_container

BASH_LANGS = {"bash", "sh", "shell"}


def _split_commands(block: str) -> list[str]:
    if block.lstrip().startswith("```"):
        block = block.split("\n", 1)[1]
    return [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def _truncate(text: str, *, max_chars=12000, head=10, tail=10) -> str:
    if len(text) <= max_chars:
        return text

    lines = text.splitlines()

    if len(lines) <= head + tail:
        half = max_chars // 2
        return f"{text[:half]}\n<Message truncated – {len(text)} chars>\n{text[-half:]}"

    snippet = lines[:head] + [f"<Message truncated – {len(lines)} lines>"] + lines[-tail:]
    return "\n".join(snippet)


def create_bash_reply(container: Container):
    def _bash_reply(recipient, messages=None, sender=None, config=None):
        if not messages:
            return False, None

        last = messages[-1].get("content") or ""
        bash_blocks = [code for lang, code in extract_code(last) if lang in BASH_LANGS]
        if not bash_blocks:
            return False, None

        logs = []
        for block in bash_blocks:
            for cmd in _split_commands(block):
                exit_code, output = run_script_in_container(container, cmd)
                logs.append(f"{output}")
                if exit_code:
                    logs[-1] = f"exit {exit_code}\n{output}"
                    reply = "❌ Bash execution halted on error:\n\n" + "\n".join(logs)
                    return True, _truncate(reply)

        return True, _truncate("✅ All commands succeeded:\n\n" + "\n".join(logs))

    return _bash_reply

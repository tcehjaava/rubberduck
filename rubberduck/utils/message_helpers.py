import re
from typing import Any, List


def strip_ansi_codes(text: str) -> str:
    if not isinstance(text, str):
        return text
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def format_content_with_indent(content: str, empty_message: str = "(Empty)", indent: str = "  ") -> str:
    if not content or not content.strip():
        return f"{indent}{empty_message}"

    if not isinstance(content, str):
        content = str(content)

    content = strip_ansi_codes(content)

    lines = content.strip().split("\n")
    formatted_lines = []

    for line in lines:
        line = line.expandtabs(4)
        formatted_lines.append(f"{indent}{line}")

    return "\n".join(formatted_lines)


def format_chat_history(chat_result: Any, indent_response: bool = True) -> str:
    if not chat_result or not hasattr(chat_result, "chat_history"):
        return "❌ No conversation history available."

    chat_history = chat_result.chat_history
    if not chat_history:
        return "❌ No conversation history available."

    formatted_lines = []

    for i, message in enumerate(chat_history):
        role = message.get("role", "unknown")
        name = message.get("name", role)
        content = message.get("content", "")

        header = f"[{i+1}] {name.upper()}"
        formatted_lines.append(f"\n{header}")
        formatted_lines.append("─" * len(header))
        formatted_lines.append(format_content_with_indent(content, "(Empty)"))
        formatted_lines.append("")

    return format_content_with_indent("\n".join(formatted_lines)) if indent_response else "\n".join(formatted_lines)


def build_all_iteration_logs(logger_memory: list) -> str:
    if not logger_memory:
        return "📄 No previous iterations logged yet."

    lines: List[str] = []

    for i, log_summary in enumerate(logger_memory, 1):
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append(f"📝 ITERATION {i} TECHNICAL LOG")
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append(format_content_with_indent(log_summary))
        lines.append("")

    return format_content_with_indent("\n".join(lines))


def build_previous_context(leader_feedback: list, logger_memory: list, last_n_iterations: int = 2) -> str:
    if not leader_feedback and not logger_memory:
        return "  🔄 This is the first iteration. No previous context available."

    lines: List[str] = []

    total_iterations = max(len(leader_feedback), len(logger_memory))
    start_idx = max(0, total_iterations - last_n_iterations)

    leader_feedback = leader_feedback[start_idx:] if leader_feedback else []
    logger_memory = logger_memory[start_idx:] if logger_memory else []

    # Combine feedback and logs by iteration
    max_iterations = max(len(leader_feedback), len(logger_memory))

    for i in range(max_iterations):
        lines.append(f"\n{'═' * 60}")
        lines.append(f"📊 ITERATION {i + 1} SUMMARY")
        lines.append(f"{'═' * 60}")

        # Add technical log if available
        if i < len(logger_memory):
            lines.append("\n🔧 Technical Log:")
            lines.append("─" * 40)
            lines.append(format_content_with_indent(logger_memory[i], "(No technical log)"))

        # Add leader feedback if available
        if i < len(leader_feedback):
            lines.append("\n📋 Leader Feedback:")
            lines.append("─" * 40)
            lines.append(format_content_with_indent(leader_feedback[i], "(No leader feedback)"))

        lines.append("")

    return format_content_with_indent("\n".join(lines))


def is_termination_msg(msg: dict, termination_marker: str = "TERMINATE") -> bool:
    if msg is None:
        return False

    content = msg.get("content")
    if content is None:
        return False

    return content.rstrip().endswith(termination_marker)


def clean_message_content(content: str | list) -> str:
    if not isinstance(content, str):
        return content

    RUNNABLE = {"bash"}

    # ── 1️⃣ multiline blocks ────────────────────────────────────────────
    multi = re.compile(
        r"(?m)^(?P<indent>[ \t]*)(?P<fence>`{3,})(?P<lang>[^\n`]*)\n"
        r"(?P<body>(?:.*?\n)*?)"
        r"(?P=indent)(?P=fence)[ \t]*$"
    )

    def _strip_or_keep(m: re.Match) -> str:
        lang = (m.group("lang") or "").strip().lower()
        return m.group(0) if lang in RUNNABLE else m.group("body")

    content = multi.sub(_strip_or_keep, content)

    # ── 2️⃣ single-line fences ( ```something``` ) ───────────────────────
    inline = re.compile(r"`{3,}([^\n`]+?)`{3,}")
    content = inline.sub(r"\1", content)

    return content

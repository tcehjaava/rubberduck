import re
from typing import Any, Iterable, List


def format_content_with_indent(content: str, empty_message: str = "(Empty)", indent: str = "  ") -> str:
    if not content or not content.strip():
        return f"{indent}{empty_message}"

    if not isinstance(content, str):
        content = str(content)

    lines = content.strip().split("\n")
    formatted_lines = []

    for line in lines:
        line = line.expandtabs(4)
        formatted_lines.append(f"{indent}{line}")

    return "\n".join(formatted_lines)


def build_previous_context(feedbacks: Iterable[str]) -> str:
    feedbacks = list(feedbacks)
    if not feedbacks:
        return "🔄 This is the first iteration. No feedback."

    lines: List[str] = ["📋 PREVIOUS FEEDBACKS FROM LEADER"]
    lines.append("─" * 50)

    for i, feedback in enumerate(feedbacks, 1):
        lines.append(f"\n📝 Feedback #{i}:")
        lines.append("┄" * 30)
        lines.append(format_content_with_indent(feedback, "(Empty feedback)"))
        lines.append("")

    return "\n".join(lines)


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


def truncate_on_send(max_chars=12000, head_lines=10, tail_lines=10):
    def _hook(*, sender, message, recipient, silent):
        def truncate_if_large(text: str) -> str:
            if len(text) <= max_chars:
                return text

            lines = text.splitlines()

            if len(lines) <= head_lines + tail_lines:
                half = max_chars // 2
                return f"{text[:half]}\n" f"<Message truncated – {len(text)} chars total>\n" f"{text[-half:]}"

            snippet = lines[:head_lines] + [f"<Message truncated – {len(lines)} lines total>"] + lines[-tail_lines:]
            return "\n".join(snippet)

        msg = message.copy() if isinstance(message, dict) else {"content": str(message)}
        content = msg.get("content")

        if isinstance(content, str) and content.strip():
            msg["content"] = truncate_if_large(content)

        return msg

    return _hook

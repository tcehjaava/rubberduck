from typing import Iterable, List


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


def is_termination_msg(msg: dict, termination_marker: str = "TERMINATE") -> bool:
    if msg is None:
        return False

    content = msg.get("content")
    if content is None:
        return False

    return content.rstrip().endswith(termination_marker)

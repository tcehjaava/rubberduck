"""Helper functions for agent-related functionality."""


def is_termination_msg(msg: dict, termination_marker: str = "TERMINATE") -> bool:
    if msg is None:
        return False

    content = msg.get("content")
    if content is None:
        return False

    return content.rstrip().endswith(termination_marker)

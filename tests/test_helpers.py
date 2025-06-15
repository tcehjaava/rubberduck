import pytest

from rubberduck.autogen.leader_executor.utils.message_helpers import is_termination_msg


@pytest.mark.parametrize(
    "message, marker, expected",
    [
        ({"content": "done"}, "TERMINATE", False),
        ({"content": "stop TERMINATE"}, "TERMINATE", True),
        (None, "TERMINATE", False),
        ({"content": "finished"}, "DONE", False),
        ({"content": "done DONE"}, "DONE", True),
    ],
)
def test_is_termination_msg(message, marker, expected):
    assert is_termination_msg(message, termination_marker=marker) is expected

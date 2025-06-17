import pytest

from rubberduck.autogen.leader_executor.utils.dataset_utils import DatasetUtils
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


for instance in [
    "django__django-15629",
    "django__django-16263",
    "pylint-dev__pylint-4551",
    "pylint-dev__pylint-6386",
    "sphinx-doc__sphinx-10673",
    "sphinx-doc__sphinx-9461",
    "sympy__sympy-13091",
    "sympy__sympy-16597",
    "sympy__sympy-20438",
    "astropy__astropy-13398",
    "django__django-11138",
    "django__django-11532",
    "django__django-11734",
    "django__django-13121",
]:
    instance = DatasetUtils.load_instance(instance_id=instance)
    print(instance.model_dump_json(indent=4))

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Iterable, List, Optional

from datasets import load_dataset
from tenacity import retry, stop_after_attempt, wait_exponential

from rubberduck.autogen.leader_executor.models.swebench_instance import (
    SWEBenchVerifiedInstance,
)

_BRACKET_MISMATCH = re.compile(r"\[[^\]]*$")


def _sanitize_node_ids(raw_ids: Iterable[str]) -> List[str]:
    fixed = []
    for nid in raw_ids:
        if _BRACKET_MISMATCH.search(nid):
            nid = nid.split("[", 1)[0]
        nid = nid.rstrip(":")
        fixed.append(nid)
    return fixed


_TEST_PROBLEM_STATEMENT = r"""
**Problem: Test Collection Script Improvements**

The `run_collect.sh` script in our pylint repo currently shows how many tests are collected and prints which tests
 cannot be collected.

Instead, I want to make these changes:

1. **Handle tests with parameters**: If a test with parameters cannot be collected, remove the parameters and try
 collecting the plain test. If the plain test works, replace the parameterized test with the plain version.

2. **Remove uncollectable tests**: If a test with parameters still cannot be collected, remove it from the list
 completely.

3. **Follow the correct format**: Tests come from `tests.env`, where parameterized tests are enclosed in quotes. Make
 sure to maintain this format when updating `tests.env`.

4. **Remove duplicates**: If both a plain test and its parameterized version exist, keep only the plain test and remove
 the parameterized one.

5. **Create a backup**: Keep a copy of the original `tests.env` file for recovery and comparison purposes.

6. **Focus on existing tests**: Only work with tests listed in `tests.env`. Trying to collect all possible tests takes
 too much time.

7. **Target goal**: Start by running the existing run_collect.sh script and after implementing all the new features the
 script should collect the same number of tests.

8. **Ensure consistency**: Running `run_collect` multiple times should give the same number of collected tests.

9. **Handle edge cases**: Account for scenarios like empty lists by writing appropriate empty lists to the file.

10. **Test thoroughly**: Run the script multiple times to verify it works as expected.

11. **Show changes**: Print the differences between old and new files, then explain why these changes will improve the
 collection process.
"""


class DatasetUtils:
    _HF_NAME = "princeton-nlp/SWE-bench_Verified"
    _DEFAULT_SPLIT = "test"

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_split(split: str, force_download: bool):
        return load_dataset(
            DatasetUtils._HF_NAME,
            split=split,
            download_mode="force_redownload" if force_download else "reuse_cache_if_exists",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=5), reraise=True)
    def load_instance(
        instance_id: str, *, split: str = _DEFAULT_SPLIT, force_download: bool = False
    ) -> Optional[SWEBenchVerifiedInstance]:
        ds = DatasetUtils._load_split(split, force_download)

        rows = ds.filter(lambda x: x["instance_id"] == instance_id)
        if len(rows) == 0:
            return None

        row = rows[0]
        row["FAIL_TO_PASS"] = json.loads(row["FAIL_TO_PASS"])
        row["PASS_TO_PASS"] = json.loads(row["PASS_TO_PASS"])
        row["FAIL_TO_PASS"] = _sanitize_node_ids(row["FAIL_TO_PASS"])
        row["PASS_TO_PASS"] = _sanitize_node_ids(row["PASS_TO_PASS"])
        row["problem_statement"] = _TEST_PROBLEM_STATEMENT.strip()

        return SWEBenchVerifiedInstance(**row)

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

**Patch-task problem statement**

Pylint’s *recursive* mode (`--recursive=y`) is ignoring all skip-lists, breaking several tests.

---

### Bug

When Pylint is run with `--recursive=y`, it still lints files and directories that should be skipped by

* `--ignore`  (base-name list),
* `--ignore-patterns`  (regex on base-name), and
* `--ignore-paths`  (regex on full path).

Consequently the following tests fail:

```
tests/lint/unittest_lint.py::test_recursive_ignore[--ignore-ignored_subdirectory]
tests/lint/unittest_lint.py::test_recursive_ignore[--ignore-patterns-ignored_*]
tests/test_self.py::TestRunTC::test_ignore_recursive
tests/test_self.py::TestRunTC::test_ignore_pattern_recursive
```

---

### Required fix

1. **Apply ignore logic inside `_discover_files`**
   File: `pylint/lint/pylinter.py`

   * `_discover_files(files_or_modules, ignore_list, ignore_list_re, ignore_paths_re)` must:

     * Skip a path if

       * its basename is in `ignore_list`, **or**
       * any regex in `ignore_list_re` matches its basename, **or**
       * any regex in `ignore_paths_re` matches the whole path.
     * Apply those checks both to every **starting argument** and to every directory / file seen
     while walking with `os.walk`.
     * When a directory is skipped, prevent descent into it by clearing `dirs[:]`.

2. **Pass the lists/regexes into `_discover_files`** from `PyLinter.check()`:

```python
if self.config.recursive:
    files_or_modules = tuple(
        self._discover_files(
            files_or_modules,
            self.config.ignore,
            self.config.ignore_patterns,
            self._ignore_paths,
        )
    )
```

3. **Add dot-directory skipping by default**
   In `pylint/lint/base_options.py`, extend the default for `ignore-patterns` to include dot-dirs:

```python
"default": (re.compile(r"^\.#"), re.compile(r"^\.")),
```

4. **Acceptance criteria**

   * All unit tests pass (`pytest` → zero failures).
   * Manual checks such as

     ```bash
     pylint --recursive=y .
     pylint --recursive=y --ignore=.a .
     pylint --recursive=y --ignore-patterns="^ignored_.*" .
     ```

     respect the ignore options and skip dot-directories out-of-the-box.

No other behaviour should change.

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

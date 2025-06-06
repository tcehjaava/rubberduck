from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Iterable, List, Optional

from datasets import load_dataset
from tenacity import retry, stop_after_attempt, wait_exponential

from rubberduck.autogen.leader_executor.models import SWEBenchVerifiedInstance

_BRACKET_MISMATCH = re.compile(r"\[[^\]]*$")


def _sanitize_node_ids(raw_ids: Iterable[str]) -> List[str]:
    fixed = []
    for nid in raw_ids:
        if _BRACKET_MISMATCH.search(nid):
            nid = nid.split("[", 1)[0]
        nid = nid.rstrip(":")
        fixed.append(nid)
    return fixed


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
        return SWEBenchVerifiedInstance(**row)

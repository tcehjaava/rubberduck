import json
from functools import cache
from typing import Optional

from datasets import load_dataset

from rubberduck.autogen.leader_executor.models import SWEBenchVerifiedInstance


class DatasetUtils:
    @staticmethod
    @cache
    def load_instance(instance_id: str) -> Optional[SWEBenchVerifiedInstance]:
        dataset = load_dataset("princeton-nlp/SWE-bench_Verified")["test"]
        for d in dataset:
            if d["instance_id"] == instance_id:
                d["FAIL_TO_PASS"] = json.loads(d["FAIL_TO_PASS"])
                d["PASS_TO_PASS"] = json.loads(d["PASS_TO_PASS"])
                return SWEBenchVerifiedInstance(**d)
        return None

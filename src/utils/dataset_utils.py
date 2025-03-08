from functools import cache
from typing import Optional, Set

from datasets import load_dataset

from models.agent_state_models import SWEBenchVerifiedInstance


class DatasetUtils:

    @staticmethod
    @cache
    def load_instance(instance_id: str) -> Optional[SWEBenchVerifiedInstance]:
        dataset = load_dataset("princeton-nlp/SWE-bench_Verified")["test"]
        for d in dataset:
            if d["instance_id"] == instance_id:
                return SWEBenchVerifiedInstance(**d)
        return None

    @staticmethod
    def extract_files(diff: str) -> Set[str]:
        files = set()
        for line in diff.split("\n"):
            if line.startswith(("+++ ", "--- ")):
                file_path = line[4:].split("\t")[0].strip()

                if file_path.startswith(("a/", "b/")):
                    file_path = file_path[2:]

                if file_path != "/dev/null":
                    files.add(file_path)
        return files

    @staticmethod
    def print_patch(instance_id: str) -> None:
        instance = DatasetUtils.load_instance(instance_id)
        if not instance:
            print(f"Instance '{instance_id}' not found.")
            return

        actual_files = DatasetUtils.extract_files(instance.patch)
        test_files = DatasetUtils.extract_files(instance.test_patch)

        print(DatasetUtils.format_files("Actual Files", actual_files))
        print(DatasetUtils.format_files("Actual Test Files", test_files))

    @staticmethod
    def format_files(title: str, files: list) -> str:
        header = f"\n==== {title} ====\n"
        content = "\n".join(sorted(files)) if files else f"(No {title.lower()})"
        footer = "=" * (10 + len(title))
        return f"{header}{content}\n{footer}\n"

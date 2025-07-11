import json
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger
from utils.dataset_utils import DatasetUtils

from rubberduck.utils.logger import setup_logger
from rubberduck.workflows.swebench import SWEBenchWorkflow


class SWEBenchEvaluator:
    def __init__(self, max_workers: int = 4, run_id: str = None):
        self.max_workers = max_workers
        self.run_id = run_id or str(uuid.uuid4())
        _, self.log_dir = setup_logger(run_id=self.run_id)
        self.workflow = SWEBenchWorkflow()

    def run_instance(self, instance_id: str) -> dict:
        thread_id = f"{instance_id}_{uuid.uuid4().hex[:8]}"
        try:
            instance = DatasetUtils.load_instance(instance_id=instance_id)

            logger.info(f"Actual SWEBench dataset patch for {instance_id}: {instance.patch}")
            logger.info(f"Actual SWEBench dataset test patch for {instance_id}: {instance.test_patch}")

            result = self.workflow.run(instance_id, thread_id, self.log_dir)
            model_patch = result.get("result", "")

            if model_patch and not model_patch.endswith("\n"):
                model_patch += "\n"

            return {
                "instance_id": instance_id,
                "model_name_or_path": "rubberduck-agent",
                "model_patch": model_patch,
            }
        except Exception:
            return {
                "instance_id": instance_id,
                "model_name_or_path": "rubberduck-agent",
                "model_patch": "",
            }

    def evaluate_instances(self, instance_ids: list[str]):
        predictions = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.run_instance, iid): iid for iid in instance_ids}

            for future in as_completed(futures):
                result = future.result()
                if result["model_patch"]:
                    predictions.append(result)

        logger.info(f"{len(predictions)}/{len(instance_ids)} successful")

        if not predictions:
            return None

        predictions_path = self.log_dir / "predictions.jsonl"
        with open(predictions_path, "w") as f:
            for pred in predictions:
                f.write(json.dumps(pred) + "\n")

        return self.run_harness(predictions_path, predictions)

    def run_harness(self, predictions_path: Path, predictions: list):
        cmd = [
            "python",
            "-m",
            "swebench.harness.run_evaluation",
            "--predictions_path",
            str(predictions_path),
            "--run_id",
            self.run_id,
            "--modal",
            "true",
            "--dataset_name",
            "princeton-nlp/SWE-bench_Verified",
            "--report_dir",
            str(self.log_dir),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("Harness completed successfully")
            logger.info(f"Output: {result.stdout}")
        else:
            logger.error(f"Harness failed: {result.returncode}")
            logger.error(f"Error: {result.stderr}")

        return result

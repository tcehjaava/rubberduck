#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ORIGINAL_PREDICTIONS = (
    "/Users/tejachava/Projects/rubberduck/logs/2025-07-02"
    "/run_20250702_173034_1821e7b7-c4e3-411a-bb55-0865bfb9ef7a/predictions.jsonl"
)
INSTANCE_ID = "django__django-14373"

print("=== SWEBench Evaluation Script ===\n")

original_path = Path(ORIGINAL_PREDICTIONS)
fixed_path = original_path.parent / "predictions_for_swebench.jsonl"

with open(original_path, "r") as f:
    pred = json.loads(f.read().strip())

fixed_pred = {
    "instance_id": pred["instance_id"],
    "model_name_or_path": pred.get("model", "rubberduck-agent"),
    "model_patch": pred.get("prediction", ""),
}

with open(fixed_path, "w") as f:
    f.write(json.dumps(fixed_pred) + "\n")

print(f"Created: {fixed_path}\n")

cmd = ["sb-cli", "submit", "swe-bench_verified", "test", "--predictions_path", str(fixed_path)]

print(f"Running: {' '.join(cmd)}\n")

process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

for line in iter(process.stdout.readline, ""):
    if line:
        print(line.rstrip())

process.wait()

print(f"\nProcess exited with code: {process.returncode}")

#!/usr/bin/env python3

import json
import re

import pandas as pd
from datasets import load_dataset
from tqdm import tqdm

_BRACKET_MISMATCH = re.compile(r"\[[^\]]*$")


def _sanitize_node_ids(raw_ids):
    fixed = []
    for nid in raw_ids:
        if _BRACKET_MISMATCH.search(nid):
            nid = nid.split("[", 1)[0]
        nid = nid.rstrip(":")
        fixed.append(nid)
    return fixed


def collect_swebench_data(output_file="swebench_data_for_rating.csv", split="test"):
    print(f"Loading SWEBench {split} split from HuggingFace...")

    dataset = load_dataset("princeton-nlp/SWE-bench_Verified", split=split)

    print(f"Found {len(dataset)} instances. Extracting data...")

    data = []

    for row in tqdm(dataset, desc="Processing instances"):
        fail_to_pass = json.loads(row["FAIL_TO_PASS"])
        pass_to_pass = json.loads(row["PASS_TO_PASS"])

        fail_to_pass = _sanitize_node_ids(fail_to_pass)
        pass_to_pass = _sanitize_node_ids(pass_to_pass)

        patch_lines = row["patch"].split("\n")
        test_patch_lines = row["test_patch"].split("\n")

        added_lines = sum(1 for line in patch_lines if line.startswith("+") and not line.startswith("+++"))
        removed_lines = sum(1 for line in patch_lines if line.startswith("-") and not line.startswith("---"))
        affected_files = len([line for line in patch_lines if line.startswith("+++") or line.startswith("---")]) // 2

        test_added_lines = sum(1 for line in test_patch_lines if line.startswith("+") and not line.startswith("+++"))

        data_row = {
            "instance_id": row["instance_id"],
            "repo": row["repo"],
            "created_at": row["created_at"],
            "problem_statement_length": len(row["problem_statement"]),
            "problem_statement_words": len(row["problem_statement"].split()),
            "problem_has_error": "Error" in row["problem_statement"] or "Traceback" in row["problem_statement"],
            "problem_has_code": "```" in row["problem_statement"] or ">>>" in row["problem_statement"],
            "patch_added_lines": added_lines,
            "patch_removed_lines": removed_lines,
            "patch_total_lines": added_lines + removed_lines,
            "patch_affected_files": affected_files,
            "num_fail_to_pass": len(fail_to_pass),
            "num_pass_to_pass": len(pass_to_pass),
            "test_patch_added_lines": test_added_lines,
            "problem_statement": (
                row["problem_statement"][:1000] + "..."
                if len(row["problem_statement"]) > 1000
                else row["problem_statement"]
            ),
            "patch": row["patch"][:1000] + "..." if len(row["patch"]) > 1000 else row["patch"],
            "test_patch": row["test_patch"][:1000] + "..." if len(row["test_patch"]) > 1000 else row["test_patch"],
            "fail_to_pass_tests": ", ".join(fail_to_pass),
            "hints_text": (
                row["hints_text"][:500] + "..."
                if row["hints_text"] and len(row["hints_text"]) > 500
                else row["hints_text"]
            ),
        }

        data.append(data_row)

    df = pd.DataFrame(data)

    df = df.sort_values("instance_id")

    df.to_csv(output_file, index=False)

    print("\n✅ Data collection complete!")
    print(f"📄 Saved {len(df)} instances to: {output_file}")
    print("\n📊 Quick statistics:")
    print(f"  - Average patch size: {df['patch_total_lines'].mean():.1f} lines")
    print(f"  - Average failing tests: {df['num_fail_to_pass'].mean():.1f}")
    print(f"  - Average problem length: {df['problem_statement_words'].mean():.0f} words")

    print("\n📋 Next steps:")
    print(f"  1. Upload '{output_file}' to Google Sheets")
    print("  2. Download and share it back for complexity rating")
    print("  3. I'll add complexity columns based on the data")

    return df


if __name__ == "__main__":
    df = collect_swebench_data(output_file="swebench_data_for_rating.csv", split="test")

    df.to_excel("swebench_data_for_rating.xlsx", index=False)
    print("\n💾 Also saved as Excel: swebench_data_for_rating.xlsx")

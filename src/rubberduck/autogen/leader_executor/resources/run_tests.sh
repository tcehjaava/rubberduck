#!/bin/bash

# Parse flags
run_fail=1; run_pass=1
[[ "$*" == *"-f"* ]] && { run_fail=1; run_pass=0; }
[[ "$*" == *"-p"* ]] && { run_fail=0; run_pass=1; }

# Load environment
source tests.env

# Build node list
nodes=()
(( run_fail )) && nodes+=("${FAIL_TO_PASS_NODES[@]}")
(( run_pass )) && nodes+=("${PASS_TO_PASS_NODES[@]}")

# Run tests
total=0; failed=()
for node in "${nodes[@]}"; do
  if out=$(pytest -q "$node" 2>&1); then
    count=$(echo "$out" | awk '/passed/ {print $1; exit}')
    total=$((total + count))
  else
    failed+=("$node")
  fi
done

# Report
if [[ ${#failed[@]} -eq 0 ]]; then
  echo "✅ $total tests passed"
else
  echo "✅ $total tests passed"
  echo "⛔ Failed nodes:"
  for f in "${failed[@]}"; do echo "  $f"; done
  exit 99
fi

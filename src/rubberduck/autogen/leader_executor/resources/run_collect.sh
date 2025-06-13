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

# Collect tests
total=0; failed=()
for node in "${nodes[@]}"; do
  if out=$(pytest --collect-only -q "$node" 2>&1); then
    count=$(echo "$out" | grep -o '[0-9]\+' | head -1)
    total=$((total + count))
  else
    failed+=("$node")
  fi
done

# Report
echo "✅ $total collected"
for f in "${failed[@]}"; do echo "⛔ $f"; done
[[ ${#failed[@]} -gt 0 ]] && exit 99

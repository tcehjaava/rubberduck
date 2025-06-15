#!/bin/bash

# Load environment
source tests.env

# Build node list
nodes=()
nodes+=("${FAIL_TO_PASS_NODES[@]}")
nodes+=("${PASS_TO_PASS_NODES[@]}")

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

#!/bin/bash

# Load environment
source tests.env

# Build node list
nodes=()
nodes+=("${FAIL_TO_PASS_NODES[@]}")
nodes+=("${PASS_TO_PASS_NODES[@]}")

# Process tests
updated_fail=()
updated_pass=()
total=0

for node in "${nodes[@]}"; do
  # Try to collect the test as-is
  if out=$(pytest --collect-only -q "$node" 2>&1); then
    count=$(echo "$out" | grep -o '[0-9]\+' | head -1)
    total=$((total + count))
    
    # Determine which array to add to
    if [[ " ${FAIL_TO_PASS_NODES[@]} " =~ " ${node} " ]]; then
      updated_fail+=("$node")
    else
      updated_pass+=("$node")
    fi
  else
    # Collection failed - check if it has parameters
    if [[ "$node" == *"["*"]"* ]]; then
      # Extract base test name (everything before '[')
      base_node="${node%%\[*}"
      
      # Try collecting the base test
      if out=$(pytest --collect-only -q "$base_node" 2>&1); then
        count=$(echo "$out" | grep -o '[0-9]\+' | head -1)
        total=$((total + count))
        
        # Add base test instead of parameterized one
        if [[ " ${FAIL_TO_PASS_NODES[@]} " =~ " ${node} " ]]; then
          updated_fail+=("$base_node")
        else
          updated_pass+=("$base_node")
        fi
        echo "✓ Replaced $node with $base_node"
      else
        # Base test also failed - skip this test entirely
        echo "⛔ Skipping $node (both parameterized and base test failed)"
      fi
    else
      # No parameters, just skip
      echo "⛔ Skipping $node (collection failed)"
    fi
  fi
done

# Remove duplicates from arrays
updated_fail=($(printf '%s\n' "${updated_fail[@]}" | sort -u))
updated_pass=($(printf '%s\n' "${updated_pass[@]}" | sort -u))

# Update tests.env with cleaned test lists
{
  echo -n "FAIL_TO_PASS_NODES=("
  for i in "${!updated_fail[@]}"; do
    if (( i > 0 )); then echo -n " "; fi
    echo -n "'${updated_fail[i]}'"
  done
  echo ")"
  
  echo -n "PASS_TO_PASS_NODES=("
  for i in "${!updated_pass[@]}"; do
    if (( i > 0 )); then echo -n " "; fi
    echo -n "'${updated_pass[i]}'"
  done
  echo ")"
} > tests.env

# Report
echo "✅ Total tests collected: $total"
echo "📝 Updated tests.env with ${#updated_fail[@]} fail-to-pass and ${#updated_pass[@]} pass-to-pass tests"

Analyze the provided input text for the explicit problem status indicator.

Look for the pattern:
PROBLEM STATUS: [SOLVED/PARTIAL/BLOCKED]

Return based on the status found:
- If "PROBLEM STATUS: SOLVED" → return "SOLVED"  
- If "PROBLEM STATUS: PARTIAL" → return "RETRY"
- If "PROBLEM STATUS: BLOCKED" → return "RETRY"

If no explicit status found, analyze the response content:
- If suggesting next iteration/checkpoint → return "RETRY"
  (e.g., "proceed with", "next checkpoint", "continue with", "next step")
- If indicating completion → return "SOLVED"
  (e.g., "problem fully solved", "all tests pass", "requirements met", "no remaining issues")

**⚠️ CRITICAL** After your response (SOLVED or RETRY), always include the keyword TERMINATE in a new line.
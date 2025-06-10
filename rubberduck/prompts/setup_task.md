Initialize the runtime by probing the entire environment—and automatically install or repair any missing tools.

* **Checklist (perform in this exact order)**
   1. **python**
      * Probe `python --version`
      * No installation ever needed; just record the version string.
   2. **ripgrep**
      * Install ripgrep
         ```bash
         apt-get -qq update && apt-get -qq install -y ripgrep
         ```
   3. **ast-grep CLI**
      * Install `ast-grep` CLI
         ```bash
         pip install --quiet --upgrade ast-grep-cli
         ```
   4. **ast_grep_rules directory**
      * Create `/workspace/ast_grep_rules` directory:
         ```bash
         mkdir -p /workspace/ast_grep_rules
         ```
   5. **tests — baseline sanity check**
      * **Install test dependencies first**
         * Look for test requirements files like `requirements_test.txt`, `requirements-test.txt`, `test-requirements.txt`, `requirements/test.txt` etc..
         * If any requirements file exists, install it:
           ```bash
           cd /workspace/<repo_name> && pip install -q -r <requirements-file>
           ```
         * Install the package in editable mode:
           ```bash
           pip install -q -e /workspace/<repo_name>
           ```
      * **Verify test collection**
         * Run collection script to ensure all tests can be discovered:
           ```bash
           cd /workspace/<repo_name> && ./run_collect.sh
           ```
         * If `pytest --collect-only` reports "ERROR collecting", strip parameter suffix (e.g. `[param]`) and retry. If now collectible, use the stripped test for testing. If still un-collectible, mark as *intentionally skipped* and move on.
      * **Establish baseline behavior**
         * Run PASS_TO_PASS baseline - should show passes:
           ```bash
           cd /workspace/<repo_name> && ./run_tests.sh -p | head -10
           ```
         * Run FAIL_TO_PASS tests - should show failures:
           ```bash
           cd /workspace/<repo_name> && ./run_tests.sh -f | head -20
           ```
      * **Verify expected pass/fail split**
         * Execute all *PASS_TO_PASS* nodes and verify they **pass**, and all *FAIL_TO_PASS* nodes and verify they **fail**
         * If any node is missing or any result deviates from the expected pass/fail split, treat it as a blocking issue and fix the environment before continuing
         * **Critical:** Verify that *every* node listed in both `PASS_TO_PASS_NODES` and `FAIL_TO_PASS_NODES` is actually collected and executed
            • If any node is skipped, mis-parsed, or "not found," treat this as a blocking issue—investigate and correct the collection problem before considering the task complete  
            • Only when all nodes execute (with the expected pass/fail outcomes) may you output the final report and declare the task finished
         * When everything is correct, note the exact commands required to re-run both sets later

After completing the checklist and validating all the items are completed, output one compact **report** strictly following the below format, Where the report starts with the below version map:

<component-1>: <version>
<component-2>: <version>
...

**Test Command Instructions:**
```
<exact-command-to-run-tests>
```

**Generated final report must only start with the version list followed by the test command instructions**, then TERMINATE; **add nothing else.** Make sure to follow all the instructions carefully.
Initialize the runtime by probing the entire environment—and automatically install or repair any missing tools.

* **Checklist (perform in this exact order)**
   1. **python**
      * Probe `python --version`
      * No installation ever needed; just record the version string.
   2. **ripgrep**
      * Probe `rg --version`
      * If the probe fails, install with
         ```bash
         apt-get -qq update && apt-get -qq install -y ripgrep
         ```
   3. **ast-grep CLI**
      * Probe `ast-grep --version`
      * Install / upgrade **if** the command is missing **or** the version is lower than `0.37`.
         Try each command in sequence; stop after the first one that succeeds.
         ```bash
         pip install --quiet --upgrade ast-grep-cli
         ```
   4. **ast_grep_rules directory**
      * Probe `test -d /workspace/ast_grep_rules`
      * If absent, create it:
         ```bash
         mkdir -p /workspace/ast_grep_rules
         ```
   5. **tests — baseline sanity check**
      * Run **one** pytest *collection pass* to obtain the full list of discovered tests.
      * Then execute all *PASS_TO_PASS* nodes and verify they **pass**, and all *FAIL_TO_PASS* nodes and verify they **fail**.
      * Confirm that **every** node named in `PASS_TO_PASS_NODES` and `FAIL_TO_PASS_NODES` appears in that collected list.
      * If any node is missing or any result deviates from the expected pass/fail split, treat it as a blocking issue and fix the environment before continuing.
      * **Critical:** Verify that *every* node listed in both `PASS_TO_PASS_NODES` and `FAIL_TO_PASS_NODES` is actually collected and executed.
         • If any node is skipped, mis-parsed, or “not found,” treat this as a blocking issue—investigate and correct the collection problem before considering the task complete.  
         • Only when all nodes execute (with the expected pass/fail outcomes) may you output the final report and declare the task finished.
      * When everything is correct, note the exact commands required to re-run both sets later.

After completing the checklist and validating all the items are completed, output one compact **report** strictly following the below format, Where the report starts with the below version map:

<component-1>: <version>
<component-2>: <version>
...

**Test Command Instructions:**
```
<exact-command-to-run-tests>
```

**Generated report must contain only the above list followed by the test command instructions**, then TERMINATE; **add nothing else.** Make sure to follow all the instructions carefully.
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

After completing the checklist, output one compact **status report** listing every
verified component and its version in the format:

<component-1>: <version>
<component-2>: <version>
...

After validating all the items are completed. Generate report must contain only the above list followed by TERMINATE;
add nothing else. Make sure to follow all the instructions carefully.
You task is to initialize the runtime by probing the entire environment—and automatically install or repair any missing tools. **Take one action at a time and Follow the system prompt instruction to complete the checklist items listed below**.

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
   5. **test dependencies**
      * Search for test requirements files in common locations:
        ```bash
        cd /workspace/<repo_name> && find . -name "*requirements*test*" -o -name "*test*requirements*" -o -name "requirements*.txt" | grep -E "(test|dev)" | head -5
        ```
      * If any requirements file exists, install it (handle failures gracefully):
        ```bash
        cd /workspace/<repo_name> && pip install -q -r <requirements-file> || echo "Warning: Failed to install from <requirements-file>"
        ```

   6. **package installation**
      * Install the package in editable mode (fix any dependency conflicts):
        ```bash
        cd /workspace/<repo_name> && pip install -q -e . || (pip install -q --upgrade setuptools wheel && pip install -q -e .)
        ```

After completing the checklist and validating all the items are completed, output one compact **report** following the below format.

<component-1>: <version>
<component-2>: <version>
...

Do not include any text before the version list. After the test command instructions, write TERMINATE;
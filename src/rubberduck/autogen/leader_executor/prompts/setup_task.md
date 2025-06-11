Your task is to initialize the runtime by probing the entire environment—and automatically install or repair any missing tools. **Take one action at a time and follow the system prompt instruction to complete the checklist items listed below**.

## **Setup Checklist**

- [ ] **Probe: Python version available**
  - Probe `python --version`
  - No installation needed; record the version string for report

- [ ] **Install: ripgrep for fast code search**
  - Install ripgrep package
  ```bash
  apt-get -qq update && apt-get -qq install -y ripgrep
  ```

- [ ] **Install: patch tool for code modifications**
  - Install patch utility (required for patch-based workflow)
  ```bash
  apt-get -qq install -y patch
  ```

- [ ] **Probe: Test requirements files**
  - Search for test dependencies in repository
  ```bash
  cd /workspace/<repo_name> && find . -name "*requirements*test*" -o -name "*test*requirements*" -o -name "requirements*.txt" | grep -E "(test|dev)" | head -5
  ```

- [ ] **Install: Test dependencies (if found)**
  - Install test requirements (handle failures gracefully)
  ```bash
  cd /workspace/<repo_name> && pip install -q -r <requirements-file> || echo "Warning: Failed to install from <requirements-file>"
  ```

- [ ] **Install: Package in editable mode**
  - Install repository package for development
  ```bash
  cd /workspace/<repo_name> && pip install -q -e . || (pip install -q --upgrade setuptools wheel && pip install -q -e .)
  ```

## **Completion Report**

**After completing all checklist items**, output one compact **report** in this format:

component-1: version
component-2: version
...

Do not include any text before the version list. After the report, write `TERMINATE` on its own line. `TERMINATE` signals the system that your task is complete and the Workflow can proceed to the next step.

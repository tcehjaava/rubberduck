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

- [ ] **Run the below command and see what's already available**
  ```
  pip list | grep pytest
  python -c "import pytest; print(pytest.__version__)"
  ```

- [ ] **Run the below command and see if there are any uncollected tests**
  ```
  ./run_collect.sh
  ```

## **Completion Report**

**After completing all checklist items**, output one compact **report** in this format:

component-1: version
component-2: version
...

Do not include any text before the version list. After the report, write `TERMINATE` on its own line. `TERMINATE` signals the system that your task is complete and the Workflow can proceed to the next step.

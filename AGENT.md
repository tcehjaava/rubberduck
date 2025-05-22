# Repository Guidelines for Agents

This repository contains **Rubberduck**, an autonomous AI software development assistant.
It is written in Python and organised as a package under the `src/` directory.

## Project Layout
- `main.py` – entry point that launches the Leader/Executor workflow.
- `src/rubberduck/autogen/leader_executor` – implementation of the Leader and Executor agents, prompts and tools.
- `src/rubberduck/langgraph/graph_orchestrator` – LangGraph based workflow orchestration utilities.
- `tests/` – pytest suite.
- `logs/` – created at runtime to store logs.

## Dependencies
Install runtime dependencies with:
```bash
pip install -r requirements.txt
```
For development and linting tools install:
```bash
pip install -r requirements-dev.txt
```
Python 3.9+ is required.

## Development Guidelines
- Code is formatted with **Black** (`line-length=120`).
- Flake8 configuration (`.flake8`) also sets `max-line-length = 120`.
- Ruff linting is configured in `pyproject.toml`.
- Tests are executed with `pytest`.

## Running the Application
To run the Leader–Executor system on a SWE-bench instance:
```bash
python main.py <instance_id>
```
`DatasetUtils` will download the SWE-bench dataset (`princeton-nlp/SWE-bench_Verified`).
Network access is required when running this command.

## Running Tests
Execute all tests with:
```bash
pytest -q
```

## Logging
Log files are written under the `logs/` directory in timestamped subfolders.

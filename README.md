# Rubberduck

Rubberduck is an autonomous AI software development assistant built in Python. It uses a Leader-Executor architecture to solve complex software engineering tasks.

## Architecture

Rubberduck leverages AutoGen and LangGraph to implement a powerful, flexible system:

- **Leader-Executor Architecture**: 
  - A Leader agent (LLM-based) breaks down complex tasks into atomic actions
  - An Executor agent handles the implementation of these actions

- **ReAct Pattern**: The Leader uses a reasoning-action loop to:
  - Analyze the current state and previous progress
  - Break down issues into manageable tasks
  - Generate the next appropriate action

- **Executor Capabilities**:
  - Execute command line operations
  - Edit and create files
  - Interact with the project codebase
  - Manage containerized environments

## Features

- SWE-Bench issue solving
- Code understanding and modification
- Workflow orchestration
- Containerized execution environment
- Repository context management

# Rubberduck 🦆

## What is Rubberduck?

Rubberduck is a multi-agent system that autonomously solves real software engineering problems. Unlike traditional AI coding assistants that require constant human guidance, Rubberduck agents work like engineering colleagues - they break down issues, explore codebases systematically, implement solutions, and validate fixes independently.

## High Level Design Diagram

```
[Issue] ──→ [Orchestrator] ──→ [Executor]
                                    │
                                    ├──→ Phase 1: Understand & Explore
                                    ├──→ Phase 2: Reproduce Issue
                                    ├──→ Phase 3: Design Solution
                                    ├──→ Phase 4: Implement Fix
                                    ├──→ Phase 5: Test & Validate
                                    │
                                    ├──→ Tools:
                                    │    ├─ Bash (commands)
                                    │    ├─ Semantic Search (find code)
                                    │    └─ Docker (safe execution)
                                    │
                                    └──→ Results
                                           │
             [Orchestrator] ←──────────────┘
                    │
                    └──→ [Leader] ──→ Review & Feedback
                                            │
             [Orchestrator] ←───────────────┘
                    │
                    ├──→ Continue? ──→ Yes ──→ (Loop)
                    └──→ Done? ──→ Yes ──→ [Output]
```

## Learn More

For a detailed explanation of the system, implementation insights, and results, check out the blog post: [From AI Copilot to AI Colleague: Building Agents That Work Like Engineers](https://medium.com/@tcehjaava/e7782925e1c9)

## Running the Project

### Prerequisites
- Python 3.9 or higher
- Docker (for safe code execution)
- API keys for Anthropic Claude models

### Setup

1. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install the app**
   ```bash
   pip install -e .
   ```

4. **Set up environment variables**
   
   Edit `rubberduck/config/.env` and replace the placeholder values with your actual API keys:
   ```
   ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here
   OPENAI_API_KEY=your_actual_openai_api_key_here
   ```

5. **Configure the system**
   
   The system uses configuration from `pyproject.toml`. Default model settings:
   - Leader Model: `claude-opus-4-20250514`
   - Executor Model: `claude-sonnet-4-20250514` 
   - Semantic Processor: `claude-3-5-haiku-20241022`
   - Logger Model: `claude-sonnet-4-20250514`

6. **Set up Modal (for harness evaluation)**
   
   Install Modal and set up your account:
   ```bash
   pip install modal
   modal setup
   ```
   Follow the setup guide: https://modal.com/docs/guide/modal-user-account-setup

### Running

Run the system with a specific instance ID:
```bash
python main.py pylint-dev__pylint-6903
```

Replace `pylint-dev__pylint-6903` with your desired SWE-bench instance ID.

---
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

---
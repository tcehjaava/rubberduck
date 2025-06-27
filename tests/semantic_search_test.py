"""
semantic_search_test.py

A minimal example demonstrating how to use the `SemanticSearch` pipeline end‑to‑end: spin up a lightweight
container, index your local codebase, and run a single semantic‑search query.

Prerequisites (install on the **host** machine, not inside the container):
  pip install docker openai langchain-core langchain-chroma langchain-openai loguru tenacity

Make sure your **OpenAI API key** is available in the environment, e.g.
  export OPENAI_API_KEY="sk‑..."

**Running the test**
───────────────────
Run from the **project root** (the directory that contains the top‑level `rubberduck/` package):

    # option 1 – preferred (module mode automatically adds the root to PYTHONPATH)
    python -m tests.semantic_search_test

    # option 2 – script mode (adds project root to `sys.path` programmatically)
    python tests/semantic_search_test.py
"""

import os
import sys
from pathlib import Path

import docker

from rubberduck.models.semantic_search_config import SemanticSearchConfig
from rubberduck.tools.semantic_search import SemanticSearch

# ────────────────────────────────────────────────────────────────────────────────
# Guarantee that the project root is on sys.path when running as a plain script.
# (If you run with `python -m tests.semantic_search_test`, this is unnecessary.)
# ────────────────────────────────────────────────────────────────────────────────
project_root = Path(__file__).resolve().parent.parent  # .. / (project‑root)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ────────────────────────────────────────────────────────────────────────────────
# Sanity‑check that the OPENAI_API_KEY is actually visible to Python before we
# touch the OpenAI client. This provides a clearer message than the low‑level
# stack‑trace if the key is missing or mis‑scoped.
# ────────────────────────────────────────────────────────────────────────────────


if not os.getenv("OPENAI_API_KEY"):
    msg = (
        "OPENAI_API_KEY is not set (or not exported in this shell). "
        "Run `export OPENAI_API_KEY=sk‑...` in the same terminal before executing "
        "the test, or pass `api_key=...` to `OpenAIEmbeddings`."
    )
    raise EnvironmentError(msg)

# Now the regular package imports work regardless of how the test is executed.


def main() -> None:
    """Index the current project directory in a temporary Docker container and
    execute a sample semantic‑search query."""

    # Spin up a lightweight container with the repo mounted read‑only at /testbed
    client = docker.from_env()
    container = client.containers.run(
        image="python:3.10-slim",
        command="sleep infinity",  # keep container alive for exec calls
        volumes={str(project_root): {"bind": "/testbed", "mode": "ro"}},
        tty=True,
        detach=True,
    )

    try:
        # Configuration and SemanticSearch instance
        config = SemanticSearchConfig()
        instance_id = "astropy__astropy-13398"
        ss = SemanticSearch(config=config, instance_id=instance_id, container=None)

        # Send a sample query
        query = "assert_allclose atol=0.1*u.mas AltAz ITRS transform"
        print(f"\nQuery: {query}\n" + "=" * 40)
        print(ss.search(query))

    finally:
        # Clean up the container regardless of success/failure
        container.kill()
        container.remove()


if __name__ == "__main__":
    main()

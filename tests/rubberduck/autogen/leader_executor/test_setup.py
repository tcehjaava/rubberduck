#!/usr/bin/env python
"""
functional_test_container_manager.py
Smoke-tests ContainerManager with SWEBench instance pydata__xarray-3095.

Run:  python functional_test_container_manager.py
"""
from __future__ import annotations

import asyncio
import logging

from rubberduck.autogen.leader_executor.utils import (
    ContainerManager,
)

INSTANCE_ID = "pydata__xarray-3095"
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def async_main() -> None:
    print(f"\n▶  Starting ContainerManager for instance: {INSTANCE_ID}\n")

    try:
        async with ContainerManager(INSTANCE_ID) as cm:
            print(f"Container name : {cm.container_name}\n")

            # 1. Python should be available
            print("Python version:", (await cm.arun("python --version")).strip())

            # 2. Verify we're inside the cloned repo
            assert (await cm.arun("git rev-parse --is-inside-work-tree")).strip() == "true"
            print("Inside Git repo: true")

            # 3. Show repo's HEAD commit (sanity check the checkout)
            print("Repo HEAD     :", (await cm.arun("git rev-parse HEAD")).strip()[:10])

            # 4. Sample command
            print("Echo test      :", (await cm.arun("echo Xarray container looks good")).strip())

        print("\n✔  Smoke-test succeeded and container cleaned up.")
    except Exception as exc:
        print(f"\n✖  Smoke-test failed: {exc}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

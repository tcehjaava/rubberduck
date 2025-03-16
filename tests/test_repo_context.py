# tests/test_repo_context.py
import logging
import sys

from config import GLOBAL_CONFIG
from repo_context.repo_fetcher import RepoFetcher
from utils import DatasetUtils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def test_repo_context(instance_id, refresh=False):
    logging.info(f"Loading instance data for {instance_id}")

    instance = DatasetUtils.load_instance(instance_id)
    if not instance:
        logging.error(f"Instance {instance_id} not found")
        return

    repo_name = f"github.com/{instance.repo}"
    commit = instance.base_commit

    logging.info(f"Testing repo context for {repo_name}@{commit}, refresh={refresh}")

    tree = RepoFetcher.fetch_repo_full(repo_name, commit, refresh)

    if tree:
        print("\nRepository Structure:")
        from repo_context import StorageManager

        print(StorageManager.format_directory_tree(tree))

        summaries = StorageManager.load_summaries(repo_name, commit)
        if summaries:
            print(f"\nSample Summaries ({min(5, len(summaries))} of {len(summaries)}):")
            for i, (path, summary) in enumerate(sorted(summaries.items())):
                if i >= 5:
                    break
                print(f"- {path}: {summary}")


if __name__ == "__main__":
    instance_id = GLOBAL_CONFIG.INSTANCE_ID
    refresh = len(sys.argv) > 1 and sys.argv[1].lower() in ("true", "refresh", "yes", "1")

    test_repo_context(instance_id, refresh)

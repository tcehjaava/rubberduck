# test_sourcegraph_query.py

import json

from tools.sourcegraph.sourcegraph_client import SourcegraphClient


def main():
    query = "repo:^github.com/pytest-dev/pytest$@c98bc4cd3d687fe9b392d8eecd905627191d4f06 (path:src/_pytest unittest OR TestCase OR tearDown OR skipped OR --pdb) -file:.*\\.md$ -file:.*\\.txt$ -file:.*\\.rst$"  # noqa: E501

    # Execute the search query
    result = SourcegraphClient.search_relevance_files(query)

    # Pretty-print the results using model_dump with indentation
    print(json.dumps(result.model_dump(), indent=4))


if __name__ == "__main__":
    main()

# test_sourcegraph_query.py

import json

from tools.sourcegraph.sourcegraph_client import SourcegraphClient


def main():
    query = "repo:^github.com/pytest-dev/pytest$@aa55975c7d3f6c9f6d7f68accc41bb7cadf0eb9a path:/_pytest/logging.py"  # noqa: E501

    # Execute the search query
    result = SourcegraphClient.get_relevance_summary(query)

    # Pretty-print the results using model_dump with indentation
    print(json.dumps(result.model_dump(), indent=4))


if __name__ == "__main__":
    main()

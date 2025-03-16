# test_sourcegraph_query.py

import json

from tools.sourcegraph_client import SourcegraphClient


def main():
    query = "repo:^github.com/django/django$@e02f67ef2d03d48128e7a118bf75f0418e24e8ac (Enum OR Choices OR Field) AND migration AND type:file"  # noqa: E501

    # Execute the search query
    result = SourcegraphClient.get_relevance_summary(query, max_files=-1)

    # Pretty-print the results using model_dump with indentation
    print(json.dumps(result.model_dump(), indent=4))


if __name__ == "__main__":
    main()

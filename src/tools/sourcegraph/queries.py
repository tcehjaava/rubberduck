# sourcegraph/queries.py

from enum import Enum


class SourcegraphQuery(Enum):
    FILE_CONTENT = """
        query ($repo: String!, $commit: String!, $path: String!) {
          repository(name: $repo) {
            commit(rev: $commit) {
              file(path: $path) {
                content
              }
            }
          }
        }
    """

    FILE_SIZE = """
        query ($repo: String!, $commit: String!, $path: String!) {
          repository(name: $repo) {
            commit(rev: $commit) {
              file(path: $path) {
                byteSize
              }
            }
          }
        }
    """

    DIRECTORY_ENTRIES = """
        query ($repo: String!, $commit: String!, $path: String!) {
          repository(name: $repo) {
            commit(rev: $commit) {
              tree(path: $path) {
                entries {
                  path
                  isDirectory
                }
              }
            }
          }
        }
    """

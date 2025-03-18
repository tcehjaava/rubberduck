import json
import logging
import os
from collections import defaultdict
from typing import List

import requests
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from config import GLOBAL_CONFIG
from tools.sourcegraph.queries import SourcegraphQuery
from utils import Utils


class RelevanceFileResult(BaseModel):
    path: str = Field(..., description="The file path in which matches were found.")
    snippets: List[str] = Field(..., description="Relevant text snippets from the file.")


class RelevanceDetailedResponse(BaseModel):
    query: str = Field(..., description="A descriptive summary of the performed query.")
    matches: int = Field(..., description="Total number of matches found in the sourcegraph query.")
    files: List[RelevanceFileResult] = Field(..., description="Top matched files with relevant snippets.")


class RelevanceQueryBlueprint(BaseModel):
    path: str = Field(..., description="The file path in which matches were found.")
    matches: int = Field(..., description="Number of matches found in the file.")
    ext: str = Field(..., description="The file extension.")


class RelevanceQueryResponse(BaseModel):
    query: str = Field(..., description="A descriptive summary of the performed query.")
    matches: int = Field(..., description="Total number of matches found in the sourcegraph query.")
    file_count: int = Field(..., description="Total number of files matched in the query.")
    files: List[RelevanceQueryBlueprint] = Field(..., description="Summary of files and their match counts.")


class SourcegraphClient:
    HEADERS = {
        "Authorization": f"token {GLOBAL_CONFIG.SOURCEGRAPH_API_TOKEN}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    @staticmethod
    @retry(wait=wait_exponential(multiplier=1, min=4, max=30), stop=stop_after_attempt(5))
    def search_relevance_files(query: str, max_files: int = 100) -> RelevanceDetailedResponse:
        url = f"{GLOBAL_CONFIG.SOURCEGRAPH_ENDPOINT}/search/stream"
        file_matches = defaultdict(list)
        path_matches = set()
        total_matches = 0

        with requests.get(url, headers=SourcegraphClient.HEADERS, params={"q": query}, stream=True) as response:
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue

                try:
                    data = json.loads(line[6:])
                    if isinstance(data, list):
                        for match in data:
                            path = match.get("path")
                            if not path:
                                continue

                            if match.get("type") == "content" and match.get("lineMatches"):
                                for lm in match["lineMatches"]:
                                    content = lm.get("line", "").strip()
                                    file_matches[path].append(content)

                            elif match.get("type") == "path":
                                path_matches.add(path)

                    elif isinstance(data, dict) and "done" in data:
                        total_matches = data.get("matchCount", 0)
                except json.JSONDecodeError as e:
                    logging.warning(f"Failed parsing JSON line: {e}")
                    continue

        for path in path_matches:
            if path not in file_matches and len(file_matches) < max_files:
                file_matches[path].append("File matched by path")

        if not file_matches and path_matches:
            for path in list(path_matches)[:max_files]:
                file_matches[path].append("File path matched. Use content search to see snippets.")

        sorted_matches = sorted(file_matches.items(), key=lambda item: len(item[1]), reverse=True)[:max_files]
        top_files = [RelevanceFileResult(path=path, snippets=snippets) for path, snippets in sorted_matches]

        return RelevanceDetailedResponse(
            query=f"Sourcegraph query: {query}",
            matches=total_matches,
            files=top_files,
        )

    @staticmethod
    @retry(wait=wait_exponential(multiplier=1, min=4, max=30), stop=stop_after_attempt(5))
    def get_relevance_summary(query: str, max_files: int = 1000) -> RelevanceQueryResponse:
        url = f"{GLOBAL_CONFIG.SOURCEGRAPH_ENDPOINT}/search/stream"
        file_counts = defaultdict(int)
        total_matches = 0

        with requests.get(url, headers=SourcegraphClient.HEADERS, params={"q": query}, stream=True) as response:
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue

                try:
                    data = json.loads(line[6:])
                    if isinstance(data, list):
                        for match in data:
                            path = match.get("path")
                            if not path:
                                continue

                            if match.get("type") == "content" and match.get("lineMatches"):
                                file_counts[path] += len(match["lineMatches"])
                            elif match.get("type") == "path":
                                file_counts[path] += 1

                    elif isinstance(data, dict) and "done" in data:
                        total_matches = data.get("matchCount", 0)
                except json.JSONDecodeError as e:
                    logging.warning(f"Failed parsing JSON line: {e}")
                    continue

        sorted_summary = sorted(file_counts.items(), key=lambda item: item[1], reverse=True)[:max_files]
        files_summary = [
            RelevanceQueryBlueprint(path=path, matches=count, ext=os.path.splitext(path)[1])
            for path, count in sorted_summary
        ]

        return RelevanceQueryResponse(
            query=f"Sourcegraph query: {query}",
            matches=total_matches,
            files=files_summary,
            file_count=len(file_counts),
        )

    @staticmethod
    @retry(wait=wait_exponential(multiplier=1, min=4, max=30), stop=stop_after_attempt(5))
    def execute_graphql_query(query: str, variables: dict) -> dict:
        try:
            response = requests.post(
                GLOBAL_CONFIG.SOURCEGRAPH_GQL_URL,
                json={"query": query, "variables": variables},
                headers=SourcegraphClient.HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"GraphQL request failed: {e}")
            raise

    @staticmethod
    def get_file_content(repo: str, commit: str, path: str) -> str:
        variables = {"repo": repo, "commit": commit, "path": path}

        response = SourcegraphClient.execute_graphql_query(
            query=SourcegraphQuery.FILE_CONTENT.value, variables=variables
        )

        content_path = ["data", "repository", "commit", "file", "content"]
        file_content = Utils.get_nested_value(response, content_path)

        if file_content is None:
            logging.error(f"Failed to retrieve file content for {path} in {repo}@{commit}. Response: {response}")
            raise ValueError(f"Failed to retrieve file content for {path}. Response: {response}")

        return file_content

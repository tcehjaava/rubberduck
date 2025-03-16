# repo_context/sourcegraph_client.py

import logging

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config import GLOBAL_CONFIG


class SourcegraphClient:
    HEADERS = {
        "Authorization": f"token {GLOBAL_CONFIG.SOURCEGRAPH_API_TOKEN}",
        "Content-Type": "application/json",
    }

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

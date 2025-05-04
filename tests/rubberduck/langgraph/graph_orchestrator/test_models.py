# test_models.py
from rubberduck.langgraph.graph_orchestrator.models import (
    IssueData,
    SearchQuery,
)

print(IssueData.schema_json(indent=2))
print(SearchQuery.schema_json(indent=2))

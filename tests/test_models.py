# test_models.py
from models import IssueData, OrchestratorResponse, SearchQuery

print(IssueData.schema_json(indent=2))
print(OrchestratorResponse.schema_json(indent=2))
print(SearchQuery.schema_json(indent=2))

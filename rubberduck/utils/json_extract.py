import json
import re
from json import JSONDecodeError
from typing import Any

from pydantic import ValidationError

from rubberduck.autogen.leader_executor.models.leader import LeaderReviewResponse


def parse_leader_response(chat_result: Any) -> LeaderReviewResponse:
    raw = getattr(chat_result, "summary", "No leader response.")

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.S)
    blob = fenced.group(1) if fenced else raw

    if fenced is None:
        start, end = blob.find("{"), blob.rfind("}") + 1
        blob = blob[start:end]

    try:
        data = json.loads(blob)
        return LeaderReviewResponse(**data)
    except (JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"Leader returned invalid or unparsable JSON. Leader Response:\n{blob}…") from exc

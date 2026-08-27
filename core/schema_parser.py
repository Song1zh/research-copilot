import json
from pydantic import ValidationError

from schemas.research_answer import ResearchCopilotAnswer
from schemas.literature_answer import LiteratureAgentAnswer


def _extract_json_object(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if text.startswith("{"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]

    return text

def parse_research_answer(raw_text: str) -> ResearchCopilotAnswer:
    data = json.loads(_extract_json_object(raw_text))
    return ResearchCopilotAnswer.model_validate(data)


def parse_literature_answer(raw_text: str) -> LiteratureAgentAnswer:
    data = json.loads(_extract_json_object(raw_text))
    return LiteratureAgentAnswer.model_validate(data)

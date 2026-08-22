import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import AgentMemoryError, remember


class AgentMemorySave(Tool):
    # D11: declared native function-calling schema (schema source-of-truth).
    native_schema = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Memory content to store."
            },
            "type": {
                "type": "string",
                "description": "Memory type (daemon vocabulary). Invalid types silently degrade to fact upstream.",
                "enum": [
                    "fact",
                    "architecture",
                    "workflow",
                    "pattern",
                    "preference",
                    "bug"
                ]
            },
            "concepts": {
                "type": "string",
                "description": "Comma-separated concept tags."
            },
            "files": {
                "type": "string",
                "description": "Comma-separated associated file paths."
            }
        },
        "required": [
            "content"
        ],
        "additionalProperties": True
    }


    async def execute(self, content="", type="fact", concepts="", files="", **kwargs):
        content = str(content or "").strip()
        if not content:
            return Response("Error: content is required", break_loop=False)
        try:
            result = await remember(
                self.agent,
                content,
                str(type or "fact"),
                _csv(concepts),
                _csv(files),
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory save failed: {error}", break_loop=False)
        return Response(json.dumps(result, indent=2, ensure_ascii=False), break_loop=False)


def _csv(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]

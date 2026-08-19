import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import AgentMemoryError, remember


class AgentMemorySave(Tool):
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

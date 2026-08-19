import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import AgentMemoryError, health


class AgentMemoryStatus(Tool):
    async def execute(self, **kwargs):
        try:
            result = await health(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory is unavailable: {error}", break_loop=False)
        return Response(json.dumps(result, indent=2, ensure_ascii=False), break_loop=False)

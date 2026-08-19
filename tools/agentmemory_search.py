import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import AgentMemoryError, search


class AgentMemorySearch(Tool):
    async def execute(self, query="", limit=10, **kwargs):
        query = str(query or "").strip()
        if not query:
            return Response("Error: query is required", break_loop=False)
        try:
            result = await search(self.agent, query, int(limit))
        except (AgentMemoryError, ValueError) as error:
            return Response(f"AgentMemory search failed: {error}", break_loop=False)
        return Response(json.dumps(result, indent=2, ensure_ascii=False), break_loop=False)

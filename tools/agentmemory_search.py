import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    memories_list,
    memory_get,
    search,
)


class AgentMemorySearch(Tool):
    """AgentMemory keyword search plus direct memory list/get by id."""

    async def execute(self, query="", limit=10, offset=0, memory_id="", operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        if operation == "list":
            return await self._list(limit, offset)
        if operation == "get":
            return await self._get(memory_id)
        if operation not in {"", "search"}:
            return Response(
                f"Error: unknown operation '{operation}'. Valid: search (default), list, get.",
                break_loop=False,
            )
        return await self._search(query, limit)

    async def _search(self, query, limit):
        query = str(query or "").strip()
        if not query:
            return Response("Error: query is required for search", break_loop=False)
        try:
            result = await search(self.agent, query, int(limit))
        except (AgentMemoryError, ValueError) as error:
            return Response(f"AgentMemory search failed: {error}", break_loop=False)
        return Response(json.dumps(result, indent=2, ensure_ascii=False), break_loop=False)

    async def _list(self, limit, offset):
        try:
            result = await memories_list(self.agent, limit=int(limit), offset=int(offset))
        except (AgentMemoryError, ValueError) as error:
            return Response(f"AgentMemory memories list failed: {error}", break_loop=False)
        memories = result.get("memories") or []
        lines = [
            f"total={result.get('total', '?')} showing {len(memories)} "
            f"(limit={result.get('limit')}, offset={result.get('offset')})"
        ]
        for m in memories:
            lines.append(
                f"- {m.get('id')} [{','.join(m.get('concepts') or [])}] "
                f"{str(m.get('content') or m.get('title') or '')[:110]}"
            )
        lines.append(
            "Tip: use operation get with memory_id for full metadata, "
            "or offset to page further."
        )
        return Response("\n".join(lines), break_loop=False)

    async def _get(self, memory_id):
        memory_id = str(memory_id or "").strip()
        if not memory_id:
            return Response("Error: memory_id is required for get", break_loop=False)
        try:
            result = await memory_get(self.agent, memory_id)
        except AgentMemoryError as error:
            return Response(f"AgentMemory memory get failed: {error}", break_loop=False)
        return Response(json.dumps(result, indent=2, ensure_ascii=False), break_loop=False)

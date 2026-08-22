import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    insights_list,
    insights_search,
    patterns,
    profile,
)


class AgentMemoryInsights(Tool):
    """Higher-order derived knowledge from AgentMemory: synthesized
    insights, recurring cross-session patterns, and the project profile."""
    # D11: declared native function-calling schema (schema source-of-truth).
    native_schema = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "description": "Operation to perform."
        },
        "limit": {
            "type": "integer"
        },
        "query": {
            "type": "string"
        }
    },
    "additionalProperties": True
}


    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "list": self._list,
            "search": self._search,
            "patterns": self._patterns,
            "profile": self._profile,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _list(self, limit=20, **kwargs):
        try:
            result = await insights_list(self.agent, _as_int(limit, 20))
        except AgentMemoryError as error:
            return Response(f"AgentMemory insights failed: {error}", break_loop=False)
        insights = result.get("insights") or []
        lines = [f"{len(insights)} insight(s):"]
        for item in insights:
            lines.append(
                f"- [{item.get('confidence', '?')}] "
                f"{str(item.get('content') or '')[:180]}"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _search(self, query="", limit=10, **kwargs):
        query = str(query or "").strip()
        if not query:
            return Response("Error: query is required", break_loop=False)
        try:
            result = await insights_search(self.agent, query, _as_int(limit, 10))
        except AgentMemoryError as error:
            return Response(f"AgentMemory insight search failed: {error}", break_loop=False)
        insights = result.get("insights") or []
        lines = [f"{len(insights)} insight(s):"]
        for item in insights:
            lines.append(
                f"- [{item.get('confidence', '?')}] "
                f"{str(item.get('content') or '')[:180]}"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _patterns(self, **kwargs):
        try:
            result = await patterns(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory patterns failed: {error}", break_loop=False)
        items = result.get("patterns") or []
        lines = [f"{len(items)} recurring pattern(s):"]
        for item in items[:15]:
            files = ", ".join(str(f) for f in (item.get("files") or [])[:4])
            lines.append(
                f"- (x{item.get('frequency', '?')}) {item.get('description', '')[:140]}"
                + (f" [{files}]" if files else "")
            )
        return Response("\n".join(lines), break_loop=False)

    async def _profile(self, **kwargs):
        try:
            result = await profile(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory profile failed: {error}", break_loop=False)
        prof = result.get("profile") or result
        lines = ["Project profile:"]
        for key in ("topConcepts", "topFiles", "commonErrors", "topTools"):
            items = prof.get(key) or []
            if items:
                rendered = ", ".join(
                    str(_item_label(i)) for i in items[:8]
                )
                lines.append(f"- {key}: {rendered}")
        summary = prof.get("summary") or prof.get("narrative") or ""
        if summary:
            lines.append(f"- summary: {str(summary)[:300]}")
        return Response("\n".join(lines), break_loop=False)


def _item_label(item):
    if isinstance(item, dict):
        return (
            item.get("concept")
            or item.get("file")
            or item.get("name")
            or item.get("tool")
            or item.get("error")
            or "?"
        )
    return str(item)


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

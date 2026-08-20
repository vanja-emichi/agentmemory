import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    sketch_create,
    sketch_list,
)


class AgentMemorySketches(Tool):
    """Ephemeral scratch graphs for planning (auto-expiring)."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "create": self._create,
            "list": self._list,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _create(self, title="", description="", **kwargs):
        title = str(title or "").strip()
        if not title:
            return Response("Error: title is required", break_loop=False)
        try:
            result = await sketch_create(
                self.agent, title, str(description or "").strip()
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory sketch create failed: {error}", break_loop=False)
        sketch = result.get("sketch") or result
        return Response(
            json.dumps(
                {
                    "created": True,
                    "sketchId": sketch.get("id"),
                    "title": sketch.get("title"),
                    "status": sketch.get("status"),
                    "expiresAt": sketch.get("expiresAt"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _list(self, limit=50, **kwargs):
        try:
            result = await sketch_list(
                self.agent, int(limit) if str(limit).strip().isdigit() else 50
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory sketch list failed: {error}", break_loop=False)
        sketches = result.get("sketches") or []
        lines = [f"{len(sketches)} sketch(es)"]
        for sketch in sketches:
            lines.append(
                f"- [{sketch.get('status', '?'):>7}] {sketch.get('title', '?')} "
                f"(id: {sketch.get('id', '?')}) actions={sketch.get('actionCount', 0)} "
                f"expires={sketch.get('expiresAt', '?')}"
            )
        return Response("\n".join(lines), break_loop=False)

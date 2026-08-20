import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    sentinel_create,
    sentinel_list,
    sentinel_trigger,
)


SENTINEL_TYPES = ("webhook", "timer", "threshold", "pattern", "approval", "custom")


class AgentMemorySentinels(Tool):
    """Event gates: watch conditions that block or unblock actions."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "create": self._create,
            "list": self._list,
            "trigger": self._trigger,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _create(self, name="", type="", config=None, linked_action_ids=None, **kwargs):
        name = str(name or "").strip()
        if not name:
            return Response("Error: name is required", break_loop=False)
        sentinel_type = str(type or "").strip().lower()
        if sentinel_type not in SENTINEL_TYPES:
            return Response(
                f"Error: type must be one of: {', '.join(SENTINEL_TYPES)}",
                break_loop=False,
            )
        cfg = config if isinstance(config, dict) else {}
        ids = linked_action_ids if isinstance(linked_action_ids, (list, tuple)) else []
        try:
            result = await sentinel_create(self.agent, name, sentinel_type, cfg, list(ids))
        except AgentMemoryError as error:
            return Response(f"AgentMemory sentinel create failed: {error}", break_loop=False)
        sentinel = result.get("sentinel") or result
        return Response(
            json.dumps(
                {
                    "created": True,
                    "sentinelId": sentinel.get("id"),
                    "name": sentinel.get("name"),
                    "type": sentinel.get("type"),
                    "status": sentinel.get("status"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _list(self, limit=50, **kwargs):
        try:
            result = await sentinel_list(
                self.agent, int(limit) if str(limit).strip().isdigit() else 50
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory sentinel list failed: {error}", break_loop=False)
        sentinels = result.get("sentinels") or []
        lines = [f"{len(sentinels)} sentinel(s)"]
        for sentinel in sentinels:
            triggered = sentinel.get("triggeredAt") or ""
            lines.append(
                f"- [{sentinel.get('status', '?'):>9}] {sentinel.get('name', '?')} "
                f"(id: {sentinel.get('id', '?')}) type={sentinel.get('type', '?')}"
                + (f" triggered={triggered}" if triggered else "")
            )
        return Response("\n".join(lines), break_loop=False)

    async def _trigger(self, sentinel_id="", value=None, **kwargs):
        sentinel_id = str(sentinel_id or "").strip()
        if not sentinel_id:
            return Response("Error: sentinel_id is required", break_loop=False)
        trigger_value = value
        if isinstance(value, str) and value.strip():
            try:
                trigger_value = float(value)
            except ValueError:
                trigger_value = value.strip()
        try:
            result = await sentinel_trigger(self.agent, sentinel_id, trigger_value)
        except AgentMemoryError as error:
            return Response(f"AgentMemory sentinel trigger failed: {error}", break_loop=False)
        sentinel = result.get("sentinel") or {}
        return Response(
            json.dumps(
                {
                    "triggered": True,
                    "sentinelId": sentinel_id,
                    "status": sentinel.get("status"),
                    "triggeredAt": sentinel.get("triggeredAt"),
                    "unblockedCount": result.get("unblockedCount", 0),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

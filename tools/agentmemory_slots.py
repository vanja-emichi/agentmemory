import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    slot_append,
    slot_create,
    slot_get,
    slot_replace,
    slots_list,
)


class AgentMemorySlots(Tool):
    """Manage AgentMemory pinned memory slots: list, get, create,
    append, replace."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "list": self._list,
            "get": self._get,
            "create": self._create,
            "append": self._append,
            "replace": self._replace,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _list(self, **kwargs):
        try:
            result = await slots_list(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory slots list failed: {error}", break_loop=False)
        slots = result.get("slots") or []
        lines = [f"{len(slots)} slot(s):"]
        for slot in slots:
            content_len = len(str(slot.get("content") or ""))
            size = slot.get("sizeLimit", "?")
            pinned = "pinned" if slot.get("pinned") else "unpinned"
            lines.append(
                f"- {slot.get('label', '?')} [{pinned}] "
                f"({content_len}/{size} chars): "
                f"{str(slot.get('description') or '')[:80]}"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _get(self, label="", **kwargs):
        label = str(label or "").strip()
        if not label:
            return Response("Error: label is required", break_loop=False)
        try:
            result = await slot_get(self.agent, label)
        except AgentMemoryError as error:
            return Response(f"AgentMemory slot get failed: {error}", break_loop=False)
        slot = result.get("slot") or result
        if not slot or (isinstance(slot, dict) and not slot.get("label")):
            return Response(f"Slot '{label}' not found.", break_loop=False)
        return Response(
            json.dumps(slot, indent=2, ensure_ascii=False), break_loop=False
        )

    async def _create(
        self, label="", content="", size_limit=2000, description="", pinned=False, **kwargs
    ):
        label = str(label or "").strip()
        if not label:
            return Response("Error: label is required", break_loop=False)
        try:
            result = await slot_create(
                self.agent,
                label,
                str(content or ""),
                _as_int(size_limit, 2000),
                str(description or ""),
                _as_bool(pinned),
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory slot create failed: {error}", break_loop=False)
        slot = result.get("slot") or result
        return Response(
            json.dumps(
                {
                    "created": True,
                    "label": slot.get("label", label),
                    "sizeLimit": slot.get("sizeLimit"),
                    "pinned": slot.get("pinned"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _append(self, label="", text="", **kwargs):
        label = str(label or "").strip()
        text = str(text or "").strip()
        if not label or not text:
            return Response("Error: label and text are required", break_loop=False)
        try:
            result = await slot_append(self.agent, label, text)
        except AgentMemoryError as error:
            return Response(f"AgentMemory slot append failed: {error}", break_loop=False)
        return Response(
            json.dumps(result, indent=2, ensure_ascii=False), break_loop=False
        )

    async def _replace(self, label="", text="", **kwargs):
        label = str(label or "").strip()
        text = str(text or "")
        if not label or not text:
            return Response("Error: label and text are required", break_loop=False)
        try:
            result = await slot_replace(self.agent, label, text)
        except AgentMemoryError as error:
            return Response(f"AgentMemory slot replace failed: {error}", break_loop=False)
        return Response(
            json.dumps(result, indent=2, ensure_ascii=False), break_loop=False
        )


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "on"}

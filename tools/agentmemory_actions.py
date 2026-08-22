import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    action_create,
    action_update,
    actions_list,
    checkpoint_create,
    checkpoint_resolve,
    crystallize,
    frontier,
    next_action,
)


class AgentMemoryActions(Tool):
    """Manage AgentMemory action items: propose, create, list, update,
    frontier and next."""
    # D11: declared native function-calling schema (schema source-of-truth).
    native_schema = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "description": "Operation to perform. One of: checkpoint, create, crystallize, frontier, list, next, update.",
            "enum": [
                "checkpoint",
                "create",
                "crystallize",
                "frontier",
                "list",
                "next",
                "update"
            ]
        },
        "title": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "priority": {
            "type": "integer"
        },
        "tags": {
            "type": "string"
        },
        "parent_id": {
            "type": "string"
        },
        "requires": {
            "type": "string"
        },
        "status": {
            "type": "string"
        },
        "limit": {
            "type": "integer"
        },
        "action_id": {
            "type": "string"
        },
        "result": {
            "type": "string"
        },
        "action_ids": {
            "type": "string"
        },
        "session_id": {
            "type": "string"
        },
        "name": {
            "type": "string"
        },
        "note": {
            "type": "string"
        }
    },
    "additionalProperties": True
}


    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "create": self._create,
            "list": self._list,
            "update": self._update,
            "frontier": self._frontier,
            "next": self._next,
            "crystallize": self._crystallize,
            "checkpoint": self._checkpoint,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _create(
        self,
        title="",
        description="",
        priority=5,
        tags="",
        parent_id="",
        requires="",
        **kwargs,
    ):
        title = str(title or "").strip()
        if not title:
            return Response("Error: title is required", break_loop=False)
        try:
            result = await action_create(
                self.agent,
                title,
                str(description or ""),
                _as_int(priority, 5),
                _csv(tags),
                str(parent_id or "").strip(),
                _csv(requires),
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory action create failed: {error}", break_loop=False)
        action = result.get("action") or result
        return Response(
            json.dumps(
                {
                    "created": True,
                    "id": action.get("id"),
                    "title": action.get("title"),
                    "priority": action.get("priority"),
                    "status": action.get("status", "pending"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _list(self, status="", limit=20, **kwargs):
        try:
            result = await actions_list(self.agent, str(status or "").strip(), _as_int(limit, 20))
        except AgentMemoryError as error:
            return Response(f"AgentMemory action list failed: {error}", break_loop=False)
        actions = result.get("actions") or []
        lines = [f"{len(actions)} action(s):"]
        for action in actions:
            lines.append(
                f"- [{action.get('status', '?'):>9}] p{action.get('priority', '?'):<2} "
                f"{action.get('title', '?')} (id: {action.get('id', '?')})"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _update(self, action_id="", status="", result="", priority=None, **kwargs):
        action_id = str(action_id or "").strip()
        if not action_id:
            return Response("Error: action_id is required", break_loop=False)
        try:
            response = await action_update(
                self.agent,
                action_id,
                str(status or "").strip(),
                str(result or ""),
                _as_int(priority, None) if priority is not None else None,
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory action update failed: {error}", break_loop=False)
        action = response.get("action") or response
        return Response(
            json.dumps(
                {
                    "updated": True,
                    "id": action.get("id", action_id),
                    "status": action.get("status", status),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _frontier(self, limit=10, **kwargs):
        try:
            result = await frontier(self.agent, _as_int(limit, 10))
        except AgentMemoryError as error:
            return Response(f"AgentMemory frontier failed: {error}", break_loop=False)
        # upstream wraps each entry as {action, blockers, leased, score}
        entries = result.get("frontier") or []
        lines = [f"Frontier ({len(entries)} unblocked action(s)):"]
        for entry in entries:
            action = entry.get("action") or {}
            lines.append(
                f"- p{action.get('priority', '?'):<2} {action.get('title', '?')} "
                f"(id: {action.get('id', '?')})"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _next(self, **kwargs):
        try:
            result = await next_action(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory next failed: {error}", break_loop=False)
        # upstream returns a flat suggestion object with actionId
        suggestion = result.get("suggestion")
        if not suggestion:
            return Response("No pending actions — the frontier is empty.", break_loop=False)
        return Response(
            json.dumps(suggestion, indent=2, ensure_ascii=False),
            break_loop=False,
        )

    async def _crystallize(self, action_ids="", session_id="", **kwargs):
        ids = _csv(action_ids)
        if not ids:
            return Response(
                "Error: action_ids is required (comma-separated list of "
                "completed action ids)",
                break_loop=False,
            )
        try:
            result = await crystallize(self.agent, ids, str(session_id or ""))
        except AgentMemoryError as error:
            return Response(f"AgentMemory crystallize failed: {error}", break_loop=False)
        crystal = result.get("crystal") or {}
        lessons = result.get("lessons") or []
        lines = [
            f"Crystal created: {crystal.get('id', '?')}",
            f"Outcomes: {len(crystal.get('keyOutcomes', []))}, "
            f"files affected: {len(crystal.get('filesAffected', []))}",
            f"Lessons generated: {len(lessons)}",
        ]
        return Response("\n".join(lines), break_loop=False)

    async def _checkpoint(
        self, name="", status="", note="", action_id="", **kwargs
    ):
        name = str(name or "").strip()
        if not name:
            return Response("Error: name is required", break_loop=False)
        status = str(status or "").strip().lower()
        try:
            if status:
                if status not in {"pending", "passed", "failed", "approved", "rejected"}:
                    return Response(
                        "Error: status must be one of pending, passed, failed, "
                        "approved, rejected",
                        break_loop=False,
                    )
                # resolve needs the checkpoint id; if the caller passed a
                # name, look up pending checkpoints to find its id
                cp_id = str(action_id or "").strip()
                if not cp_id.startswith("ckpt_"):
                    cp_id = await self._find_checkpoint_id(name) or ""
                if not cp_id:
                    return Response(
                        f"Error: no checkpoint found named '{name}' to resolve",
                        break_loop=False,
                    )
                result = await checkpoint_resolve(
                    self.agent, cp_id, status, str(note or "")
                )
                action = "resolved"
            else:
                result = await checkpoint_create(
                    self.agent, name, str(action_id or "") if str(action_id or "").startswith("act_") else "", "", str(note or "")
                )
                action = "created"
        except AgentMemoryError as error:
            return Response(
                f"AgentMemory checkpoint failed: {error}", break_loop=False
            )
        checkpoint = result.get("checkpoint") or result
        return Response(
            json.dumps(
                {
                    action: True,
                    "id": checkpoint.get("id"),
                    "name": checkpoint.get("name", name),
                    "status": checkpoint.get("status"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _find_checkpoint_id(self, name: str) -> str:
        try:
            result = await actions_list(self.agent, "", 1)  # warm conn
        except Exception:
            pass
        try:
            from usr.plugins.agentmemory.helpers.client import request as _request
            data = await _request(
                self.agent, "/agentmemory/checkpoints", method="GET", timeout=10
            )
            for cp in data.get("checkpoints") or []:
                if cp.get("name") == name:
                    return str(cp.get("id") or "")
        except Exception:
            pass
        return ""


def _csv(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

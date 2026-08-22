import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    routine_create,
    routine_list,
    routine_run,
)


class AgentMemoryRoutines(Tool):
    """Frozen workflows: named step sequences that materialize as actions."""
    # D11: declared native function-calling schema (schema source-of-truth).
    native_schema = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "description": "Operation to perform."
        },
        "name": {
            "type": "string"
        },
        "steps": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "limit": {
            "type": "integer"
        },
        "routine_id": {
            "type": "string"
        },
        "initiated_by": {
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
            "run": self._run,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _create(self, name="", steps=None, description="", **kwargs):
        name = str(name or "").strip()
        if not name:
            return Response("Error: name is required", break_loop=False)
        step_list = steps if isinstance(steps, (list, tuple)) else []
        if not step_list:
            return Response("Error: steps is required (non-empty array)", break_loop=False)
        # Normalize: each step must be an object with at least a title
        normalized = []
        for step in step_list:
            if isinstance(step, str):
                normalized.append({"title": step})
            elif isinstance(step, dict) and str(step.get("title", "")).strip():
                normalized.append(step)
            else:
                return Response(
                    "Error: each step must have a title (string or object with title field)",
                    break_loop=False,
                )
        try:
            result = await routine_create(
                self.agent, name, normalized, str(description or "").strip()
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory routine create failed: {error}", break_loop=False)
        routine = result.get("routine") or result
        return Response(
            json.dumps(
                {
                    "created": True,
                    "routineId": routine.get("id"),
                    "name": routine.get("name"),
                    "steps": len(routine.get("steps") or []),
                    "frozen": routine.get("frozen"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _list(self, limit=50, **kwargs):
        try:
            result = await routine_list(
                self.agent, int(limit) if str(limit).strip().isdigit() else 50
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory routine list failed: {error}", break_loop=False)
        routines = result.get("routines") or []
        lines = [f"{len(routines)} routine(s)"]
        for routine in routines:
            lines.append(
                f"- {routine.get('name', '?')} (id: {routine.get('id', '?')}) "
                f"steps={len(routine.get('steps') or [])}"
                f" frozen={'yes' if routine.get('frozen') else 'no'}"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _run(self, routine_id="", initiated_by="", **kwargs):
        routine_id = str(routine_id or "").strip()
        if not routine_id:
            return Response("Error: routine_id is required", break_loop=False)
        try:
            result = await routine_run(
                self.agent, routine_id, str(initiated_by or "").strip()
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory routine run failed: {error}", break_loop=False)
        run = result.get("run") or {}
        return Response(
            json.dumps(
                {
                    "started": True,
                    "runId": run.get("id"),
                    "routineId": run.get("routineId"),
                    "status": run.get("status"),
                    "actionsCreated": result.get("actionsCreated", 0),
                    "actionIds": run.get("actionIds", []),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

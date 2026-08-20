import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import AgentMemoryError, diagnose, health


class AgentMemoryStatus(Tool):
    """AgentMemory health and diagnostics."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        if operation in {"", "health"}:
            return await self._health()
        if operation == "diagnose":
            return await self._diagnose()
        return Response(
            f"Error: unknown operation '{operation}'. Valid: health, diagnose.",
            break_loop=False,
        )

    async def _health(self):
        try:
            result = await health(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory is unavailable: {error}", break_loop=False)
        return Response(json.dumps(result, indent=2, ensure_ascii=False), break_loop=False)

    async def _diagnose(self):
        try:
            result = await diagnose(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory diagnostics failed: {error}", break_loop=False)
        # render the checks compactly
        lines = ["AgentMemory diagnostics:"]
        checks = (
            result.get("checks")
            or result.get("results")
            or result.get("categories")
            or []
        )
        if isinstance(checks, dict):
            checks = [dict(name=k, **(v if isinstance(v, dict) else {"status": v})) for k, v in checks.items()]
        for check in checks[:30]:
            name = str(check.get("name") or check.get("check") or check.get("id") or "?")[:50]
            status = str(check.get("status") or check.get("result") or "?")
            mark = "OK " if status.lower() in {"ok", "pass", "passed", "healthy", "true"} else "WARN"
            lines.append(f"[{mark}] {name}: {status}")
        if not checks:
            lines.append(json.dumps(result, ensure_ascii=False)[:1200])
        return Response("\n".join(lines), break_loop=False)

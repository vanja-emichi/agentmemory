import datetime
import json
import os

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    audit_list,
    diagnose,
    export_state,
    health,
)


class AgentMemoryStatus(Tool):
    """AgentMemory health, metrics, audit, diagnostics, export."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        if operation in {"", "health"}:
            return await self._health()
        if operation == "metrics":
            return await self._metrics()
        if operation == "audit":
            return await self._audit(**kwargs)
        if operation == "diagnose":
            return await self._diagnose()
        if operation == "export":
            return await self._export()
        return Response(
            f"Error: unknown operation '{operation}'. Valid: health, metrics, audit, diagnose, export.",
            break_loop=False,
        )

    async def _health(self):
        try:
            result = await health(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory is unavailable: {error}", break_loop=False)
        return Response(json.dumps(result, indent=2, ensure_ascii=False), break_loop=False)

    async def _metrics(self):
        """Function-level observability derived from health.functionMetrics."""
        try:
            result = await health(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory metrics failed: {error}", break_loop=False)
        h = result.get("health") or {}
        metrics = result.get("functionMetrics") or h.get("functionMetrics") or []
        lines = [
            f"status={result.get('status', '?')} uptime={round(h.get('uptimeSeconds', 0) / 3600, 1)}h",
            f"heap={round((h.get('memory') or {}).get('heapUsed', 0) / 1048576, 1)}MB/"
            f"{round((h.get('memory') or {}).get('heapTotal', 0) / 1048576, 1)}MB "
            f"rss={round((h.get('memory') or {}).get('rss', 0) / 1048576, 1)}MB "
            f"lag={round(h.get('eventLoopLagMs', 0), 1)}ms",
            f"{len(metrics)} function metric(s):",
        ]
        for m in metrics[:20]:
            fid = str(m.get("id") or m.get("functionId") or m.get("name") or "?")[:40]
            ok = m.get("ok", m.get("successes", "?"))
            fail = m.get("failed", m.get("failures", "?"))
            avg = m.get("avgMs", m.get("avgDurationMs", "?"))
            q = m.get("avgQuality", m.get("quality", ""))
            qtxt = f" q={round(q, 1)}" if isinstance(q, (int, float)) else ""
            lines.append(f"- {fid}: ok={ok} fail={fail} avg={avg}ms{qtxt}")
        return Response("\n".join(lines), break_loop=False)

    async def _audit(self, limit=50, action_id="", **kwargs):
        """Action change trail (who/what/when with before-after)."""
        try:
            result = await audit_list(
                self.agent,
                int(limit) if str(limit).strip().isdigit() else 50,
                str(action_id or "").strip(),
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory audit failed: {error}", break_loop=False)
        entries = result.get("entries") or []
        lines = [f"{len(entries)} audit entr{'y' if len(entries) == 1 else 'ies'}"
                 + (f" for {action_id}" if action_id else "")]
        for e in entries[:30]:
            ts = str(e.get("timestamp", ""))[:19]
            op = e.get("operation", "?")
            actor = (e.get("details") or {}).get("actor") or "?"
            targets = ",".join(str(t)[:24] for t in (e.get("targetIds") or [])[:3])
            lines.append(f"- {ts} [{op}] by {actor} -> {targets}")
        return Response("\n".join(lines), break_loop=False)

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

    async def _export(self):
        """Full-state backup; saves JSON to workdir and reports counts."""
        try:
            result = await export_state(self.agent)
        except AgentMemoryError as error:
            return Response(f"AgentMemory export failed: {error}", break_loop=False)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join("/a0/usr/workdir", f"agentmemory-export-{stamp}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except OSError as error:
            return Response(f"Export fetched but save failed: {error}", break_loop=False)
        lines = [f"Export saved: {path}", f"version={result.get('version', '?')} exportedAt={result.get('exportedAt', '?')}"]
        for key, value in sorted(result.items()):
            if isinstance(value, list):
                lines.append(f"- {key}: {len(value)}")
        return Response("\n".join(lines), break_loop=False)

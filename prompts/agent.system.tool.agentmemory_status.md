# AgentMemory Status

Use `agentmemory_status` for server health, function-level metrics, the audit trail, deep diagnostics, and full-state export.

### Operations
- `operation: "health"` (default) — daemon status, uptime, memory, workers.
- `operation: "metrics"` — function-level observability (per-function ok/fail counts, avg duration, quality) derived from health.
- `operation: "audit"` — action change trail (who/what/when). Args: `limit` (default 50), `action_id` (filter to one action).
- `operation: "diagnose"` — full subsystem consistency checks.
- `operation: "export"` — full-state backup; saves JSON to the workdir (`agentmemory-export-<timestamp>.json`) and reports collection counts. Use before risky operations or for migration.

usage:
~~~json
{
  "thoughts": ["The daemon has been under load; I should check function-level metrics."],
  "headline": "Checking AgentMemory function metrics",
  "tool_name": "agentmemory_status",
  "tool_args": {
    "operation": "metrics"
  }
}
~~~

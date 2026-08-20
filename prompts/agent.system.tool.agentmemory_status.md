## AgentMemory status
Use `agentmemory_status` to check AgentMemory server health and run subsystem diagnostics.

### Operations
- `operation: "health"` (default, no args needed) — server reachable + healthy
- `operation: "diagnose"` — full subsystem checks (consistency, indexes, graph, retention)

When diagnosing memory problems (missing observations, stale search results, graph gaps), run `diagnose` first.

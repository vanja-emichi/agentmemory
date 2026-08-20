## AgentMemory leases
Use `agentmemory_leases` to claim exclusive ownership of an action so parallel agents never duplicate work.

### Operations
- `operation: "acquire"` — claim the action. Args: `action_id` (required, must be pending), `agent_id` (defaults to this agent), `ttl_seconds` (default 600).
- `operation: "renew"` — extend an active lease before it expires. Same args as acquire.
- `operation: "release"` — give up the lease. Args: `action_id`, `agent_id`, optional `result` (marks the action done).

### When to use
- Before starting work on a frontier action: acquire first; on failure the lease expires automatically.
- Long tasks: renew periodically so the action is not considered abandoned.
- Done or handing off: release with a `result` summary so the next agent sees the outcome.

usage:
~~~json
{
  "thoughts": ["Claiming this action before starting work."],
  "headline": "Acquiring lease on action",
  "tool_name": "agentmemory_leases",
  "tool_args": {
    "operation": "acquire",
    "action_id": "act_...",
    "ttl_seconds": 900
  }
}
~~~

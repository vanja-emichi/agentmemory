## AgentMemory signals
Use `agentmemory_signals` for inter-agent messaging when A0 subordinates must coordinate through AgentMemory.

### Operations
- `operation: "send"` — send a signal. Args: `content` (required), `to` (recipient agent id; omit for broadcast), `type` (info, request, response, alert, handoff), `reply_to` (signal id to thread on).
- `operation: "read"` — read (and mark read) signals. Args: `agent_id` (defaults to this agent), `unread_only`, `thread_id`, `limit`.
- `operation: "threads"` — list conversation threads. Args: `agent_id`.

### When to use
- Delegate then notify: send `type: "handoff"` when passing work to a subordinate's action.
- After completing a task: send `type: "response"` back to the coordinator.
- Alert on failures or blockers: `type: "alert"`.
- Subordinates should `read` at task start to pick up assignments and reply in-thread with `reply_to`.

usage:
~~~json
{
  "thoughts": ["Need to notify the subordinate of its assignment."],
  "headline": "Sending handoff signal to subordinate",
  "tool_name": "agentmemory_signals",
  "tool_args": {
    "operation": "send",
    "to": "agent-1",
    "type": "handoff",
    "content": "You own act_...: implement the login form"
  }
}
~~~

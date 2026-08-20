# AgentMemory Sketches (ephemeral planning graphs)

Use `agentmemory_sketches` for ephemeral scratch graphs — lightweight planning containers that auto-expire (~1 hour TTL). Unlike persistent knowledge graphs, sketches are disposable by design.

### Operations
- `operation: "create"` — create a sketch. Args: `title` (required), `description`.
- `operation: "list"` — list sketches. Arg: `limit`.

Note: daemon 0.9.29 exposes only create and list for sketches; no update/delete/get-by-id routes. Sketches expire automatically (see `expiresAt` in responses).

### When to use
- Planning: sketch out a task decomposition before committing to durable actions/routines.
- Scratch state: temporary working context that should not pollute long-term memory.
- Brainstorming: iterate freely — the TTL cleans up automatically.

usage:
~~~json
{
  "thoughts": ["Let me sketch the task decomposition before committing to actions."],
  "headline": "Creating planning sketch",
  "tool_name": "agentmemory_sketches",
  "tool_args": {
    "operation": "create",
    "title": "Refactor plan",
    "description": "Scratch decomposition of the auth refactor"
  }
}
~~~

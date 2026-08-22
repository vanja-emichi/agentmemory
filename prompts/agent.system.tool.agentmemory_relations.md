## AgentMemory relations
Use `agentmemory_relations` to link related memories so the Relations dashboard tab and memory traversal reflect how knowledge connects.

### Operations
- `operation: "relate"` — create a typed link between two memories. Args: `source_id`, `target_id`, `relation_type` (supersedes, extends, derives, contradicts, related), optional `confidence` (0..1; computed from shared sessions/age when omitted).
- `operation: "list"` — list existing relations. Args: `limit`.

### When to use
- After `agentmemory_save` returns a memory id that builds on an earlier memory: relate them (`extends` / `derives`).
- When new knowledge replaces an old belief: `supersedes` (source = newer, target = older).
- When a memory contradicts a stored one: `contradicts`.
- Use memory ids (`mem_...`) from save/search results. Relations are never created automatically (except evolve's supersedes chains) — linking is the agent's job.

usage:
~~~json
{
  "thoughts": ["This memory extends the architecture note."],
  "headline": "Linking related memories",
  "tool_name": "agentmemory_relations",
  "tool_args": {
    "operation": "relate",
    "source_id": "mem_new123",
    "target_id": "mem_old456",
    "relation_type": "extends"
  }
}
~~~

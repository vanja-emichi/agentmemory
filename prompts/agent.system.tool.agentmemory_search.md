## AgentMemory search
Use `agentmemory_search` when prior project context, decisions, lessons, or sessions may answer the current task, or when you need to page through / fetch stored memories by id.
Operations:
- default / `search`: `query` (required), `limit` (default 10) — keyword search
- `list`: page through all memories without a query. Args: `limit` (default 20, max 100), `offset`
- `get`: fetch one memory with full metadata. Arg: `memory_id`
Only report memories returned by the tool. If there are no matches, say so instead of guessing.

usage:
~~~json
{
  "thoughts": ["I want to see everything stored so far, not just keyword matches."],
  "headline": "Listing stored memories",
  "tool_name": "agentmemory_search",
  "tool_args": {
    "operation": "list",
    "limit": 20
  }
}
~~~

## AgentMemory team
Use `agentmemory_team` for shared team memory across agents: publish useful items and browse what others shared.

### Operations
- `operation: "share"` — share an item with the team. Args: `item_id` (required), `item_type` (observation, memory, pattern).
- `operation: "feed"` — recent shared items. Args: `limit`.
- `operation: "profile"` — team profile: members, top concepts, shared patterns. Args: optional `agent_id`.

### When to use
- After producing a broadly useful finding (memory id from `agentmemory_save`): share it so every agent sees it in the feed.
- At coordination points: check `feed`/`profile` before duplicating discovery work.

usage:
~~~json
{
  "thoughts": ["This finding helps every agent on the team."],
  "headline": "Sharing memory with team",
  "tool_name": "agentmemory_team",
  "tool_args": {
    "operation": "share",
    "item_id": "mem_...",
    "item_type": "memory"
  }
}
~~~

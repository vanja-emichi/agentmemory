## AgentMemory recall (deep lookups)
Use `agentmemory_recall` for historical questions beyond basic keyword search: unified hybrid search, file histories, session walkthroughs, timeline traversal, and git-commit linkage.

### Operations
- `operation: "search"` — hybrid semantic+keyword search across memories/lessons/observations/insights. Args: `query` (required), `mode` (compact/expanded), `limit`
- `operation: "file"` — past observations about a file ("what happened to this file?"). Arg: `path` (required)
- `operation: "session"` — observations of one session. Args: `session_id` (required), `limit`
- `operation: "timeline"` — chronological walk around an observation anchor. Args: `anchor` (observation id from `session`), `limit`
- `operation: "commits"` — recent commits linked to agent sessions. Arg: `limit`
- `operation: "commit_lookup"` — which session produced a commit. Arg: `sha` (required)

### When to use
- "What do we know about X?" → `search` (richer than basic agentmemory_search)
- "Why does this file look like this / what changed here before?" → `file`
- "What did we do in that session?" → `session` (session ids appear in memory search results)
- "Which session made this commit?" → `commit_lookup`

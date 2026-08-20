## AgentMemory slots
Use `agentmemory_slots` to read and write persistent pinned memory slots. Slots are size-limited text units injected at session start (when pinned) and maintained across sessions. The slot-reflect pipeline auto-appends TODOs to `pending_items` and records patterns; this tool is your explicit read/write access.

Default slots: `persona` (role/tone), `user_preferences`, `tool_guidelines`, `project_context`, `guidance` (active advice), `pending_items` (unfinished work), `session_patterns`, `self_notes`.

### Operations
- `operation: "list"` — all slots with sizes and pinned status
- `operation: "get"` — read one slot. Arg: `label`
- `operation: "create"` — new slot. Args: `label`, `content`, `size_limit` (default 2000, max 20000), `description`, `pinned` (true/false)
- `operation: "append"` — append text. Args: `label`, `text`
- `operation: "replace"` — replace full content. Args: `label`, `text`

### When to use
- When the user states a durable preference, convention, or rule: update the matching slot (`user_preferences`, `tool_guidelines`) — this is the highest-fidelity way to remember user preferences
- When you learn a project-level fact (architecture decision, build command): update `project_context`
- When planning multi-session work: keep `pending_items` current
- Read `guidance` and `pending_items` when resuming work or choosing next steps
- Slot writes fail if content exceeds `size_limit` — use `replace` with curated content rather than endless appends

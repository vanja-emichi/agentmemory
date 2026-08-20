## AgentMemory lessons
Use `agentmemory_lessons` to consult and manage lessons — confidence-weighted rules derived from corrections, crystals, and recurring patterns. Lessons are the distilled "what we learned" layer.

### Operations
- `operation: "recall"` — search lessons. Args: `query` (required), `limit`
- `operation: "save"` — save a lesson. Args: `content` (required), `context`, `confidence` (0-1, default 0.6)
- `operation: "delete"` — soft-delete. Arg: `lesson_id`

### When to use
- **Before repeating similar work**: recall lessons about the tools, repos, or error patterns involved — past sessions may have already solved this
- **After a correction or hard-won insight**: save it as a lesson so future sessions start smarter
- When a user corrects you, that is a strong lesson signal — capture it
- Lessons auto-decay (Ebbinghaus curve); important ones can be reinforced by re-saving with higher confidence

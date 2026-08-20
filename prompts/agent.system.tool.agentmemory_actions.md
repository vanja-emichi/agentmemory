## AgentMemory actions
Use `agentmemory_actions` to manage persistent action items in AgentMemory. Actions are cross-session work items with priority (1-10), status (pending/active/done/blocked/cancelled) and optional dependencies. They feed the Frontier (unblocked work) and crystallize into lessons when done.

### Operations
- `operation: "create"` — create an action. Args: `title` (required), `description`, `priority` (1-10, default 5), `tags` (csv), `parent_id`, `requires` (csv of action ids that must finish first).
- `operation: "list"` — list actions. Args: optional `status` filter, `limit`.
- `operation: "update"` — update an action. Args: `action_id` (required), `status`, `result` (outcome when completing), `priority`.
- `operation: "frontier"` — unblocked actions ranked by priority. Arg: `limit`.
- `operation: "next"` — single most important next action.
- `operation: "crystallize"` — distill completed action chains into a crystal + auto-generated lessons. Args: `action_ids` (required, comma-separated), `session_id` (optional)

### When to PROPOSE actions (active behavior)
You must proactively surface action-worthy work instead of waiting for the user to ask. When you finish a meaningful task, discover follow-up work, notice deferred TODOs, or the user mentions future plans, propose actions to the user in your response BEFORE creating them:

1. Detect: completed work worth tracking, explicit TODOs/deferred items, user-stated plans, risks or follow-ups you noticed.
2. Propose in your reply: a short list with title, why, suggested priority. Example: "I suggest tracking 2 follow-ups as actions: (1) <title> (p8) — <why>; (2) <title> (p5) — <why>. Create them?"
3. Wait for confirmation, then create via this tool with the agreed titles/priorities.
4. When you complete tracked work, mark it done with a concise `result` summary.
5. When a meaningful action chain is fully done, offer to crystallize it ("crystallize this?" — produces a durable digest + lessons).

Rules: propose at most 3-5 actions at once; only propose genuinely useful cross-session work (not routine single-reply answers); if the user declines, do not re-propose the same item in that chat; never create actions silently without user approval unless the user already asked you to track something.

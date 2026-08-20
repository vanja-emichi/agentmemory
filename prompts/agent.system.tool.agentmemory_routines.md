# AgentMemory Routines (frozen workflows)

Use `agentmemory_routines` to save named step sequences and run them later. Running a routine materializes its steps as actions (with dependencies), so routine work becomes trackable and resumable.

### Operations
- `operation: "create"` — create a routine. Args: `name` (required), `steps` (required: array of strings or objects with `title`; optional `description`, `dependsOn`), `description`.
- `operation: "list"` — list routines. Arg: `limit`.
- `operation: "run"` — run a routine now. Args: `routine_id` (required), `initiated_by` (optional agent id).

Note: daemon 0.9.29 does not expose update/delete/get-by-id routes for routines; only create, list, and run are available.

### Step schema
Each step is either a plain string (used as title) or an object:
- `title` (required) — what the step does
- `description` (optional) — detail
- `dependsOn` (optional) — array of step order numbers that must complete first

### When to use
- Recurring procedures: save a release checklist or deploy sequence as a routine, run it each time.
- Multi-step plans: crystallize a successful workflow into a routine for reuse.
- Delegation prep: run a routine to materialize actions, then dispatch subordinates per action.

Run response includes `actionsCreated` and `actionIds` — the materialized action items ready for execution.

usage:
~~~json
{
  "thoughts": ["I should save this recurring release checklist as a routine."],
  "headline": "Creating release-checklist routine",
  "tool_name": "agentmemory_routines",
  "tool_args": {
    "operation": "create",
    "name": "release-checklist",
    "steps": [
      {
        "title": "Run full test suite"
      },
      {
        "title": "Bump version",
        "dependsOn": [0]
      }
    ],
    "description": "Standard release procedure"
  }
}
~~~

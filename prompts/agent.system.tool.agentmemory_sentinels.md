# AgentMemory Sentinels (event gates)

Use `agentmemory_sentinels` to watch conditions and gate actions on external events. Sentinels complement leases: leases claim work; sentinels decide *when* work becomes eligible.

### Operations
- `operation: "create"` — create a sentinel. Args: `name` (required), `type` (required: webhook | timer | threshold | pattern | approval | custom), `config` (dict, per type), `linked_action_ids` (csv list of action ids to unblock on trigger).
- `operation: "list"` — list sentinels. Arg: `limit`.
- `operation: "trigger"` — fire a sentinel now. Args: `sentinel_id` (required), `value` (the observed value; for threshold types).

Note: daemon 0.9.29 does not expose update/delete/get-by-id routes for sentinels; only create, list, and trigger are available.

### Config schemas by type
- `threshold`: `{"metric": "heapUsedMB", "operator": "gt"|"lt"|"eq", "value": 400}` — numeric gate.
- `timer`: `{"durationMs": 3600000}` — fires after elapsed time.
- `pattern`: `{"pattern": "error.*timeout"}` — regex gate over observed text.
- `webhook`: `{"path": "/ci-done"}` — fires when the daemon receives that webhook path.
- `approval`: `{}` — fires when a human approves (triggered via the trigger op or UI).
- `custom`: free-form config for user-defined checks.

### When to use
- CI/CD gating: create a webhook sentinel for pipeline completion, link the deploy action.
- Health thresholds: create a threshold sentinel on daemon metrics, link an incident action.
- Deferred waits: "watch for X, then do Y" — sentinel for X, action for Y.

Trigger response includes `unblockedCount` — how many linked actions became eligible.

## AgentMemory save
Use `agentmemory_save` for durable facts, decisions, corrections, or lessons that will help future work.
args: `content` (required), optional `type`, `concepts` (comma-separated), and `files` (comma-separated)

### Types (must match the daemon's vocabulary)
- `fact` — default; standalone durable knowledge
- `architecture` — system structure and design decisions
- `workflow` — how a process runs end to end
- `pattern` — recurring behavior across sessions; procedural consolidation (Procedures tab) only runs when ≥2 pattern memories recur, so save recurring observations explicitly as `pattern`
- `preference` — stable user preference
- `bug` — known defect or pitfall

Any other type silently degrades to `fact` upstream — stick to this list.
Skip greetings, transient progress, secrets, and facts already obvious from the repository.

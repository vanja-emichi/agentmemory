## AgentMemory insights
Use `agentmemory_insights` for higher-order derived knowledge: synthesized insights (patterns across memories/lessons/crystals), recurring cross-session file-patterns, and the project profile.

### Operations
- `operation: "list"` — recent synthesized insights. Arg: `limit`
- `operation: "search"` — search insights. Args: `query` (required), `limit`
- `operation: "patterns"` — recurring file co-change patterns across sessions (which files change together, how often)
- `operation: "profile"` — project profile: top concepts, files, common errors

### When to use
- Before planning refactors: `patterns` shows which files move together — change them as a unit
- When onboarding to unfamiliar parts of a project: `profile` summarizes what matters
- When hunting systemic issues: `search` insights for the domain (e.g., "auth", "build failures")
- After finishing significant work: check whether new insights crystallized

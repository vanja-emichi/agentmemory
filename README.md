# AgentMemory plugin

Connects Agent Zero to [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory) through its local REST API.

## Setup

Start AgentMemory separately:

```bash
npx -y @agentmemory/agentmemory
```

The plugin uses `http://localhost:3111` for a host install and `http://host.docker.internal:3111` inside Docker. The repository's Docker compose file already maps `host.docker.internal` to the host gateway. Configure the URL, secret, project-scoped behavior, and recall/capture toggles in the AgentMemory plugin settings. `AGENTMEMORY_URL`, `AGENTMEMORY_SECRET`, and `AGENTMEMORY_AGENT_ID` override the corresponding settings.

The plugin injects context at the start of each Agent Zero turn, records the user prompt and tool results, and closes the AgentMemory session when the turn ends. It also exposes `agentmemory_search`, `agentmemory_save`, and `agentmemory_status`.

Agent Zero's bundled `_memory` plugin is a separate memory backend. Disable one backend if both are enabled, otherwise the agent may receive duplicate recall and save the same information twice.

## Memory panel (WebUI)

Adds a **Memory** surface to the right canvas (next to Files / Editor / Factory / Desktop):

- live server health badge (healthy / degraded / offline)
- searchable memory list (`search` is proxied server-side)
- recent captured sessions with observation counts
- read-only by design: the proxy whitelists `health`, `memories`, `sessions`, `observations` (GET) and `search` (POST); all write endpoints return 403

Panel files: `extensions/webui/right-canvas-panels/agentmemory-panel.html`, `extensions/webui/right_canvas_register_surfaces/register-agentmemory.js`, modal fallback `webui/main.html` + standalone `webui/panel.html`, backend proxy `api/proxy.py`. The proxy target follows the plugin `url` setting (or `AGENTMEMORY_URL` env). Requires the AgentMemory server to be running.

## Auto-start server

When `auto_start` is enabled (default) and the configured URL points at this container (`localhost`/`127.0.0.1`/`::1`), the plugin keeps the AgentMemory server alive:

- **At framework boot**: `extensions/python/startup_migration/_10_agentmemory_server.py` runs `ensure_server()` in a daemon thread (boot never blocks).
- **Self-heal**: the first turn of each chat re-checks health and revives the server in the background if it died.
- The server is spawned detached (`start_new_session=True`) and writes to `<workdir>/agentmemory.log`.

Remote URLs are never spawned — auto-start only manages a container-local server. Data persists in `<workdir>/data/`, so memories and sessions survive restarts.

## Actions tool (proactive proposals)

`agentmemory_actions` gives the agent first-class management of AgentMemory action items (cross-session work with priority, status, dependencies):

- `create` / `list` / `update` / `frontier` / `next` operations, mirroring upstream's `memory_action_create`/`memory_action_update`/`memory_frontier`/`memory_next` MCP tools
- **Propose-then-confirm etiquette** baked into the tool prompt: the agent proactively proposes action-worthy follow-ups at natural moments (completed work, TODOs, user-stated plans) and only creates them after user approval
- When `auto_recall` is on and pending actions exist, the session-start context injection surfaces the frontier (top 5) so the agent can propose continuing open work in any future chat

## Relations tool

`agentmemory_relations` links memories so the dashboard Relations tab and memory traversal reflect how knowledge connects:

- `relate` — create a typed link between two memory ids (`supersedes`, `extends`, `derives`, `contradicts`, `related`), optional explicit `confidence` (otherwise computed from shared sessions/age)
- `list` — browse existing relations

Relations are never created automatically by the daemon (except `supersedes` chains from memory evolution) — the client is expected to relate the knowledge it connects. This tool is that wiring.

## Memory types and procedural consolidation

`agentmemory_save` uses the daemon's exact type vocabulary: `fact`, `architecture`, `workflow`, `pattern`, `preference`, `bug`. Any other type silently degrades to `fact` upstream. `pattern` matters: procedural consolidation (the dashboard Procedures tab) only runs when ≥2 memories of type `pattern` recur (frequency ≥2) — save recurring behaviors explicitly as `pattern`.

## LLM timeout

The daemon's default LLM timeout is 60s; consolidation prompts are large and slow providers can exceed it (intermittent `Semantic consolidation failed` / `LLM graph extraction failed`). Auto-start spawns the daemon with `AGENTMEMORY_LLM_TIMEOUT_MS=120000`; override via the daemon's own environment to raise or lower it.

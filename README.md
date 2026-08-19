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

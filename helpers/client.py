from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from helpers import plugins, projects, settings as a0_settings


PLUGIN_NAME = "agentmemory"
SESSION_ID_KEY = "agentmemory_session_id"
MAX_ERROR_LENGTH = 240


class AgentMemoryError(RuntimeError):
    pass


def get_config(agent: Any) -> dict[str, Any]:
    raw = plugins.get_plugin_config(PLUGIN_NAME, agent=agent, caller="agent") or {}
    return {
        "enabled": _as_bool(raw.get("enabled", True), True),
        "url": os.getenv("AGENTMEMORY_URL") or str(raw.get("url") or _default_url()),
        "secret": os.getenv("AGENTMEMORY_SECRET") or str(raw.get("secret") or ""),
        "agent_id": os.getenv("AGENTMEMORY_AGENT_ID") or str(raw.get("agent_id") or ""),
        "auto_recall": _as_bool(raw.get("auto_recall", True), True),
        "auto_capture": _as_bool(raw.get("auto_capture", True), True),
        "recall_budget": max(1, _as_int(raw.get("recall_budget", 1500), 1500)),
    }


def _default_url() -> str:
    return "http://host.docker.internal:3111" if os.path.exists("/.dockerenv") else "http://localhost:3111"


def get_scope(agent: Any) -> tuple[str, str]:
    project_name = projects.get_context_project_name(agent.context)
    if project_name:
        cwd = projects.get_project_folder(project_name)
    else:
        cwd = a0_settings.get_settings()["workdir_path"]
        project_name = os.path.basename(os.path.abspath(cwd)) or "agent-zero"
    return project_name, os.path.abspath(cwd)


def get_session_id(agent: Any) -> str:
    return str(agent.get_data(SESSION_ID_KEY) or agent.context.id)


async def start_session(agent: Any, title: str = "") -> dict[str, Any]:
    config = get_config(agent)
    project, cwd = get_scope(agent)
    payload: dict[str, Any] = {
        "sessionId": get_session_id(agent),
        "project": project,
        "cwd": cwd,
    }
    if title.strip():
        payload["title"] = title.strip()[:200]
    if config["agent_id"].strip():
        payload["agentId"] = config["agent_id"].strip()
    return await request(agent, "/agentmemory/session/start", payload, timeout=2)


async def end_session(agent: Any) -> dict[str, Any]:
    return await request(
        agent,
        "/agentmemory/session/end",
        {"sessionId": get_session_id(agent)},
        timeout=2,
    )


async def observe(agent: Any, hook_type: str, data: Any) -> dict[str, Any]:
    project, cwd = get_scope(agent)
    payload: dict[str, Any] = {
        "hookType": hook_type,
        "sessionId": get_session_id(agent),
        "project": project,
        "cwd": cwd,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    if get_config(agent)["agent_id"].strip():
        payload["agentId"] = get_config(agent)["agent_id"].strip()
    return await request(agent, "/agentmemory/observe", payload, timeout=2)


async def search(agent: Any, query: str, limit: int = 10) -> dict[str, Any]:
    project, cwd = get_scope(agent)
    payload: dict[str, Any] = {
        "query": query,
        "limit": max(1, min(100, int(limit))),
        "project": project,
        "cwd": cwd,
        "format": "full",
    }
    if get_config(agent)["agent_id"].strip():
        payload["agentId"] = get_config(agent)["agent_id"].strip()
    return await request(agent, "/agentmemory/search", payload, timeout=10)


async def remember(
    agent: Any,
    content: str,
    memory_type: str = "fact",
    concepts: list[str] | None = None,
    files: list[str] | None = None,
) -> dict[str, Any]:
    project, _ = get_scope(agent)
    payload: dict[str, Any] = {
        "content": content,
        "type": memory_type or "fact",
        "concepts": concepts or [],
        "files": files or [],
        "project": project,
    }
    if get_config(agent)["agent_id"].strip():
        payload["agentId"] = get_config(agent)["agent_id"].strip()
    return await request(agent, "/agentmemory/remember", payload, timeout=10)


async def actions_list(agent: Any, status: str = "", limit: int = 20) -> dict[str, Any]:
    """List actions, optionally filtered by status."""
    params = [f"limit={limit}"]
    if status:
        params.append(f"status={status}")
    return await request(
        agent, f"/agentmemory/actions?{'&'.join(params)}", method="GET", timeout=10
    )


async def action_create(
    agent: Any,
    title: str,
    description: str = "",
    priority: int = 5,
    tags: list | None = None,
    parent_id: str = "",
    requires: list | None = None,
) -> dict[str, Any]:
    """Create an action item (mirrors upstream memory_action_create)."""
    payload = {
        "title": title,
        "description": description,
        "priority": priority,
        "project": get_scope(agent)[0],
        "createdBy": f"a0-agent-{getattr(agent, 'number', 0)}",
    }
    if tags:
        payload["tags"] = tags
    if parent_id:
        payload["parentId"] = parent_id
    if requires:
        payload["requires"] = requires
    return await request(agent, "/agentmemory/actions", payload, timeout=15)


async def action_update(
    agent: Any,
    action_id: str,
    status: str = "",
    result: str = "",
    priority: int | None = None,
) -> dict[str, Any]:
    """Update an action (mirrors upstream memory_action_update)."""
    payload: dict = {"actionId": action_id}
    if status:
        payload["status"] = status
    if result:
        payload["result"] = result
    if priority is not None:
        payload["priority"] = priority
    return await request(agent, "/agentmemory/actions/update", payload, timeout=15)


async def frontier(agent: Any, limit: int = 10) -> dict[str, Any]:
    """Unblocked actions ranked by priority (mirrors memory_frontier)."""
    return await request(
        agent, f"/agentmemory/frontier?limit={limit}", method="GET", timeout=10
    )


async def next_action(agent: Any) -> dict[str, Any]:
    """Single most important next action (mirrors memory_next)."""
    return await request(agent, "/agentmemory/next", method="GET", timeout=10)


# ---------------------------------------------------------------- slots


async def slots_list(agent: Any) -> dict[str, Any]:
    """List all memory slots (mirrors memory_slot_list)."""
    return await request(agent, "/agentmemory/slots", method="GET", timeout=10)


async def slot_get(agent: Any, label: str) -> dict[str, Any]:
    """Read one slot by label (mirrors memory_slot_get)."""
    return await request(
        agent, f"/agentmemory/slot?label={urllib.parse.quote(label)}", method="GET", timeout=10
    )


async def slot_create(
    agent: Any,
    label: str,
    content: str = "",
    size_limit: int = 2000,
    description: str = "",
    pinned: bool = False,
) -> dict[str, Any]:
    """Create a new slot (mirrors memory_slot_create)."""
    payload = {
        "label": label,
        "content": content,
        "sizeLimit": size_limit,
        "description": description,
        "pinned": pinned,
        "scope": get_scope(agent)[0],
    }
    return await request(agent, "/agentmemory/slot", payload, timeout=15)


async def slot_append(agent: Any, label: str, text: str) -> dict[str, Any]:
    """Append text to a slot (mirrors memory_slot_append)."""
    payload = {"label": label, "text": text, "scope": get_scope(agent)[0]}
    return await request(agent, "/agentmemory/slot/append", payload, timeout=15)


async def slot_replace(agent: Any, label: str, text: str) -> dict[str, Any]:
    """Replace slot content (mirrors memory_slot_replace)."""
    payload = {"label": label, "content": text, "scope": get_scope(agent)[0]}
    return await request(agent, "/agentmemory/slot/replace", payload, timeout=15)


# --------------------------------------------------------------- lessons


async def lesson_save(
    agent: Any, content: str, context: str = "", confidence: float = 0.6
) -> dict[str, Any]:
    """Save a lesson (mirrors memory_lesson_save)."""
    payload = {
        "content": content,
        "context": context,
        "confidence": confidence,
        "project": get_scope(agent)[0],
    }
    return await request(agent, "/agentmemory/lessons", payload, timeout=15)


async def lesson_search(agent: Any, query: str, limit: int = 10) -> dict[str, Any]:
    """Search lessons (mirrors memory_lesson_recall)."""
    payload = {"query": query, "limit": limit}
    return await request(agent, "/agentmemory/lessons/search", payload, timeout=15)


async def lesson_delete(agent: Any, lesson_id: str) -> dict[str, Any]:
    """Soft-delete a lesson (mirrors memory_lesson_delete)."""
    return await request(agent, "/agentmemory/lessons/delete", {"lessonId": lesson_id}, timeout=15)


# ------------------------------------------------------------ crystallize


async def crystallize(
    agent: Any, action_ids: list[str], session_id: str = ""
) -> dict[str, Any]:
    """Crystallize completed action chains (mirrors memory_crystallize)."""
    payload = {"actionIds": action_ids, "project": get_scope(agent)[0]}
    if session_id:
        payload["sessionId"] = session_id
    return await request(agent, "/agentmemory/crystals/create", payload, timeout=90)


# ------------------------------------------------------------- deep lookups


async def smart_search(
    agent: Any, query: str, mode: str = "compact", limit: int = 10
) -> dict[str, Any]:
    """Hybrid semantic+keyword search (mirrors memory_smart_search)."""
    payload = {"query": query, "mode": mode, "limit": limit}
    return await request(agent, "/agentmemory/smart-search", payload, timeout=20)


async def file_context(agent: Any, path: str) -> dict[str, Any]:
    """Past observations about a file (mirrors memory_file_history)."""
    payload = {"path": path}
    return await request(agent, "/agentmemory/file-context", payload, timeout=15)


async def timeline(agent: Any, anchor: str, limit: int = 20) -> dict[str, Any]:
    """Chronological traversal around an observation anchor
    (mirrors memory_timeline)."""
    payload = {"anchor": anchor, "limit": limit}
    return await request(agent, "/agentmemory/timeline", payload, timeout=15)


async def observations(agent: Any, session_id: str, limit: int = 50) -> dict[str, Any]:
    """Observations of a session (raw timeline source)."""
    return await request(
        agent,
        f"/agentmemory/observations?sessionId={urllib.parse.quote(session_id)}&limit={limit}",
        method="GET",
        timeout=15,
    )


async def commits_list(agent: Any, limit: int = 20) -> dict[str, Any]:
    """Recent commits linked to sessions (mirrors memory_commits)."""
    return await request(agent, f"/agentmemory/commits?limit={limit}", method="GET", timeout=10)


async def session_by_commit(agent: Any, sha: str) -> dict[str, Any]:
    """Find the session that produced a commit (mirrors
    memory_commit_lookup)."""
    return await request(
        agent, f"/agentmemory/session/by-commit?sha={urllib.parse.quote(sha)}", method="GET", timeout=10
    )


# ------------------------------------------------------------ tier 2 lookups


async def insights_list(agent: Any, limit: int = 20) -> dict[str, Any]:
    """List synthesized insights (mirrors memory_insight_list)."""
    return await request(agent, f"/agentmemory/insights?limit={limit}", method="GET", timeout=10)


async def sentinel_list(agent: Any, limit: int = 50) -> dict[str, Any]:
    return await request(agent, f"/agentmemory/sentinels?limit={int(limit)}", method="GET", timeout=15)


async def sentinel_create(
    agent: Any,
    name: str,
    sentinel_type: str,
    config: dict[str, Any] | None = None,
    linked_action_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "type": sentinel_type}
    if config:
        payload["config"] = config
    if linked_action_ids:
        payload["linkedActionIds"] = linked_action_ids
    return await request(agent, "/agentmemory/sentinels", payload, timeout=15)


async def sentinel_update(
    agent: Any,
    sentinel_id: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    return await request(agent, f"/agentmemory/sentinels/{sentinel_id}", fields, method="PUT", timeout=15)


async def sentinel_delete(agent: Any, sentinel_id: str) -> dict[str, Any]:
    return await request(agent, f"/agentmemory/sentinels/{sentinel_id}", {}, method="DELETE", timeout=15)


async def sentinel_trigger(agent: Any, sentinel_id: str, value: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"sentinelId": sentinel_id}
    if value is not None:
        payload["value"] = value
    return await request(agent, "/agentmemory/sentinels/trigger", payload, timeout=15)


async def routine_list(agent: Any, limit: int = 50) -> dict[str, Any]:
    return await request(agent, f"/agentmemory/routines?limit={int(limit)}", method="GET", timeout=15)


async def routine_create(
    agent: Any,
    name: str,
    steps: list[dict[str, Any]],
    description: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "steps": steps}
    if description:
        payload["description"] = description
    return await request(agent, "/agentmemory/routines", payload, timeout=15)


async def routine_run(agent: Any, routine_id: str, initiated_by: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {"routineId": routine_id}
    if initiated_by:
        payload["initiatedBy"] = initiated_by
    return await request(agent, "/agentmemory/routines/run", payload, timeout=30)


async def sketch_list(agent: Any, limit: int = 50) -> dict[str, Any]:
    return await request(agent, f"/agentmemory/sketches?limit={int(limit)}", method="GET", timeout=15)


async def sketch_create(agent: Any, title: str, description: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {"title": title}
    if description:
        payload["description"] = description
    return await request(agent, "/agentmemory/sketches", payload, timeout=15)


async def insights_search(agent: Any, query: str, limit: int = 10) -> dict[str, Any]:
    """Search insights (mirrors memory_insight_search)."""
    payload = {"query": query, "limit": limit}
    return await request(agent, "/agentmemory/insights/search", payload, timeout=15)


async def patterns(agent: Any) -> dict[str, Any]:
    """Recurring patterns across sessions (mirrors memory_patterns)."""
    return await request(agent, "/agentmemory/patterns", {}, timeout=20)


async def profile(agent: Any) -> dict[str, Any]:
    """Project profile: top concepts/files/errors (mirrors memory_profile)."""
    project = get_scope(agent)[0]
    return await request(
        agent, f"/agentmemory/profile?project={urllib.parse.quote(project)}", method="GET", timeout=15
    )


async def graph_query(agent: Any, limit: int = 25, node_type: str = "") -> dict[str, Any]:
    """Query the knowledge graph (mirrors memory_graph_query)."""
    payload: dict = {"limit": limit}
    if node_type:
        payload["type"] = node_type
    return await request(agent, "/agentmemory/graph/query", payload, timeout=15)


async def diagnose(agent: Any) -> dict[str, Any]:
    """Run subsystem health checks (mirrors memory_diagnose)."""
    return await request(agent, "/agentmemory/diagnostics", {}, timeout=30)


async def checkpoint_create(
    agent: Any, name: str, action_id: str = "", status: str = "", note: str = ""
) -> dict[str, Any]:
    """Create an external checkpoint gating an action (mirrors
    memory_checkpoint)."""
    payload: dict = {"name": name}
    if action_id:
        payload["actionId"] = action_id
    if status:
        payload["status"] = status
    if note:
        payload["note"] = note
    return await request(agent, "/agentmemory/checkpoints", payload, timeout=15)


async def checkpoint_resolve(
    agent: Any, checkpoint_id: str, status: str, note: str = ""
) -> dict[str, Any]:
    """Resolve a checkpoint (CI result, approval, deploy status)."""
    payload: dict = {"checkpointId": checkpoint_id, "status": status}
    if note:
        payload["note"] = note
    return await request(agent, "/agentmemory/checkpoints/resolve", payload, timeout=15)


async def health(agent: Any) -> dict[str, Any]:
    return await request(agent, "/agentmemory/health", method="GET", timeout=3)


async def request(
    agent: Any,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    method: str = "POST",
    timeout: float,
) -> dict[str, Any]:
    config = get_config(agent)
    url = f"{config['url'].rstrip('/')}/{path.lstrip('/')}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AgentMemoryError("AgentMemory URL must be an HTTP or HTTPS URL")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Agentmemory-Source": "agent-zero",
    }
    if config["secret"]:
        headers["Authorization"] = f"Bearer {config['secret']}"

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    return await asyncio.to_thread(_request, url, method, headers, body, timeout)


def _request(
    url: str,
    method: str,
    headers: dict[str, str],
    body: bytes | None,
    timeout: float,
) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise AgentMemoryError(
            f"AgentMemory HTTP {error.code}: {detail[:MAX_ERROR_LENGTH]}"
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise AgentMemoryError(f"AgentMemory unavailable: {error}") from None

    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        raise AgentMemoryError("AgentMemory returned invalid JSON") from None
    if not isinstance(value, dict):
        raise AgentMemoryError("AgentMemory returned an unexpected response")
    return value


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return default if value is None else bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---- Tier 3: multi-agent coordination (signals, leases, team) ----


def default_agent_id(agent: Any) -> str:
    """Stable agent identity for signals/leases/team calls."""
    config = get_config(agent)
    if config["agent_id"].strip():
        return config["agent_id"].strip()
    number = getattr(agent, "agent_number", 0) or 0
    return "a0" if number == 0 else f"agent-{number}"


async def signal_send(
    agent: Any,
    from_id: str,
    content: str,
    to: str = "",
    type_: str = "",
    reply_to: str = "",
) -> dict[str, Any]:
    """Send a signal to another agent or broadcast (mirrors
    memory_signal_send)."""
    payload: dict = {"from": from_id, "content": content}
    if to:
        payload["to"] = to
    if type_:
        payload["type"] = type_
    if reply_to:
        payload["replyTo"] = reply_to
    return await request(agent, "/agentmemory/signals/send", payload, timeout=10)


async def signal_read(
    agent: Any,
    agent_id: str,
    unread_only: bool = False,
    thread_id: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """Read (and mark read) signals for an agent (mirrors
    memory_signal_read)."""
    params = [f"agentId={urllib.parse.quote(agent_id)}", f"limit={limit}"]
    if unread_only:
        params.append("unreadOnly=true")
    if thread_id:
        params.append(f"threadId={urllib.parse.quote(thread_id)}")
    return await request(
        agent, f"/agentmemory/signals?{'&'.join(params)}", method="GET", timeout=10
    )


async def signal_threads(agent: Any, agent_id: str) -> dict[str, Any]:
    """List conversation threads for an agent (mirrors signal-threads)."""
    return await request(
        agent,
        f"/agentmemory/signals/threads?agentId={urllib.parse.quote(agent_id)}",
        method="GET",
        timeout=10,
    )


async def lease_acquire(
    agent: Any, action_id: str, agent_id: str, ttl_seconds: int = 600
) -> dict[str, Any]:
    """Acquire an exclusive lease on an action (mirrors memory_lease)."""
    payload = {"actionId": action_id, "agentId": agent_id, "ttlSeconds": ttl_seconds}
    return await request(agent, "/agentmemory/leases/acquire", payload, timeout=15)


async def lease_renew(
    agent: Any, action_id: str, agent_id: str, ttl_seconds: int = 600
) -> dict[str, Any]:
    """Renew an active lease, extending its expiry."""
    payload = {"actionId": action_id, "agentId": agent_id, "ttlSeconds": ttl_seconds}
    return await request(agent, "/agentmemory/leases/renew", payload, timeout=15)


async def lease_release(
    agent: Any, action_id: str, agent_id: str, result: str = ""
) -> dict[str, Any]:
    """Release a lease (optionally marking the action done)."""
    payload = {"actionId": action_id, "agentId": agent_id}
    if result:
        payload["result"] = result
    return await request(agent, "/agentmemory/leases/release", payload, timeout=15)


async def team_share(agent: Any, item_id: str, item_type: str) -> dict[str, Any]:
    """Share a memory/observation/pattern with the team (mirrors
    memory_team_share)."""
    payload = {"itemId": item_id, "itemType": item_type}
    return await request(agent, "/agentmemory/team/share", payload, timeout=15)


async def team_feed(agent: Any, limit: int = 20) -> dict[str, Any]:
    """Recent shared items from team members (mirrors memory_team_feed)."""
    agent_id = default_agent_id(agent)
    return await request(
        agent,
        f"/agentmemory/team/feed?agentId={urllib.parse.quote(agent_id)}&limit={limit}",
        method="GET",
        timeout=15,
    )


async def team_profile(agent: Any, agent_id: str = "") -> dict[str, Any]:
    """Team profile: members, top concepts, shared patterns."""
    agent_id = agent_id or default_agent_id(agent)
    return await request(
        agent,
        f"/agentmemory/team/profile?agentId={urllib.parse.quote(agent_id)}",
        method="GET",
        timeout=15,
    )

import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    commits_list,
    file_context,
    graph_query,
    observations,
    session_by_commit,
    smart_search,
    timeline,
)


class AgentMemoryRecall(Tool):
    """Deep historical lookups into AgentMemory: unified smart search,
    file history, session observations, timeline traversal, and commit
    linkage."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "search": self._search,
            "file": self._file,
            "session": self._session,
            "timeline": self._timeline,
            "commits": self._commits,
            "commit_lookup": self._commit_lookup,
            "graph": self._graph,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _search(self, query="", mode="compact", limit=10, **kwargs):
        query = str(query or "").strip()
        if not query:
            return Response("Error: query is required", break_loop=False)
        try:
            result = await smart_search(
                self.agent, query, str(mode or "compact"), _as_int(limit, 10)
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory smart search failed: {error}", break_loop=False)
        # smart-search returns mixed buckets; render compactly
        lines = []
        for bucket in ("memories", "lessons", "observations", "insights", "sessions"):
            items = result.get(bucket) or []
            if items:
                lines.append(f"{bucket} ({len(items)}):")
                for item in items[:5]:
                    if isinstance(item, dict):
                        text = (
                            item.get("content")
                            or item.get("title")
                            or item.get("narrative")
                            or item.get("text")
                            or ""
                        )
                        lines.append(f"  - {str(text)[:150]}")
        if not lines:
            lines.append("No results found.")
        return Response("\n".join(lines), break_loop=False)

    async def _file(self, path="", **kwargs):
        path = str(path or "").strip()
        if not path:
            return Response("Error: path is required", break_loop=False)
        try:
            result = await file_context(self.agent, path)
        except AgentMemoryError as error:
            return Response(f"AgentMemory file history failed: {error}", break_loop=False)
        files = result.get("files") or []
        context = str(result.get("context") or "").strip()
        lines = [f"{len(files)} file match(s)"]
        if context:
            lines.append(context[:1500])
        for item in files[:10]:
            lines.append(json.dumps(item, ensure_ascii=False)[:250])
        return Response("\n".join(lines), break_loop=False)

    async def _session(self, session_id="", limit=50, **kwargs):
        session_id = str(session_id or "").strip()
        if not session_id:
            return Response("Error: session_id is required", break_loop=False)
        try:
            result = await observations(self.agent, session_id, _as_int(limit, 50))
        except AgentMemoryError as error:
            return Response(
                f"AgentMemory session observations failed: {error}", break_loop=False
            )
        obs = result.get("observations") or []
        lines = [f"{len(obs)} observation(s):"]
        for item in obs:
            title = str(item.get("title") or item.get("narrative") or "")[:120]
            lines.append(f"- [{item.get('timestamp', '?')[:19]}] {title}")
        return Response("\n".join(lines), break_loop=False)

    async def _timeline(self, anchor="", limit=20, **kwargs):
        anchor = str(anchor or "").strip()
        if not anchor:
            return Response(
                "Error: anchor is required (an observation id; get one from the "
                "session operation first)",
                break_loop=False,
            )
        try:
            result = await timeline(self.agent, anchor, _as_int(limit, 20))
        except AgentMemoryError as error:
            return Response(f"AgentMemory timeline failed: {error}", break_loop=False)
        entries = result.get("entries") or []
        lines = [f"{len(entries)} timeline entr(ies):"]
        for item in entries:
            title = str(item.get("title") or item.get("narrative") or "")[:120]
            lines.append(f"- [{item.get('timestamp', '?')[:19]}] {title}")
        return Response("\n".join(lines), break_loop=False)

    async def _commits(self, limit=20, **kwargs):
        try:
            result = await commits_list(self.agent, _as_int(limit, 20))
        except AgentMemoryError as error:
            return Response(f"AgentMemory commits failed: {error}", break_loop=False)
        commits = result.get("commits") or []
        lines = [f"{len(commits)} commit link(s):"]
        for item in commits:
            lines.append(json.dumps(item, ensure_ascii=False)[:250])
        return Response("\n".join(lines), break_loop=False)

    async def _commit_lookup(self, sha="", **kwargs):
        sha = str(sha or "").strip()
        if not sha:
            return Response("Error: sha is required", break_loop=False)
        try:
            result = await session_by_commit(self.agent, sha)
        except AgentMemoryError as error:
            return Response(f"AgentMemory commit lookup failed: {error}", break_loop=False)
        sessions = result.get("sessions") or result.get("session") or []
        if not sessions:
            return Response(
                result.get("error") or f"No sessions linked to commit {sha}.",
                break_loop=False,
            )
        if isinstance(sessions, dict):
            sessions = [sessions]
        lines = [f"{len(sessions)} session(s) linked to {sha}:"]
        for item in sessions:
            lines.append(json.dumps(item, ensure_ascii=False)[:300])
        return Response("\n".join(lines), break_loop=False)

    async def _graph(self, limit=25, node_type="", **kwargs):
        try:
            result = await graph_query(self.agent, _as_int(limit, 25), str(node_type or ""))
        except AgentMemoryError as error:
            return Response(f"AgentMemory graph query failed: {error}", break_loop=False)
        nodes = result.get("nodes") or []
        edges = result.get("edges") or []
        lines = [
            f"Graph: {len(nodes)} node(s), {len(edges)} edge(s) "
            f"(total {result.get('totalNodes', '?')}/{result.get('totalEdges', '?')})"
        ]
        for node in nodes[:20]:
            name = str(node.get("name") or "?")[:60]
            lines.append(f"- [{node.get('type', '?')}] {name}")
        return Response("\n".join(lines), break_loop=False)


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

"""Passthrough proxy for the embedded AgentMemory viewer dashboard.

The embedded viewer (served by viewer.py) rewrites its /agentmemory/* REST
calls to this handler so everything stays same-origin with the WebUI.

Security posture mirrors proxy.py (the simple panel proxy): read-only.
- GET paths: any read-style endpoint (health, memories, sessions, timeline,
  observations, graph, lessons, audit, actions, replay, profile, flags...).
- POST paths: whitelisted read-style POST endpoints only (search-style
  queries; AgentMemory exposes many reads via POST).
- Everything mutating (remember, forget, evict, delete, crystallize,
  consolidate, snapshot, migrate, heal, lease...) is refused with 403.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from flask import Request, Response

from helpers.api import ApiHandler

DEFAULT_TARGET = "http://localhost:3111"
TIMEOUT_SECONDS = 20

# Read endpoints the viewer and panel use (GET). Names follow the exact
# literals in the viewer bundle (livez, config/flags, semantic, ...).
GET_PATHS = {
    "health",
    "livez",
    "liveness",
    "memories",
    "memory-by-id",
    "sessions",
    "session/by-commit",
    "timeline",
    "observations",
    "graph/stats",
    "graph/query",
    "lessons",
    "lesson-list",
    "relations",
    "relations-list",
    "actions",
    "action-list",
    "action-get",
    "crystals",
    "crystal-list",
    "crystal-get",
    "audit",
    "profile",
    "semantic",
    "semantic-list",
    "procedural",
    "procedural-list",
    "insight-list",
    "insight-search",
    "patterns",
    "commits",
    "snapshots",
    "config/flags",
    "config-flags",
    "frontier",
    "replay/sessions",
    "replay/load",
    "viewer",
}

# Read/query endpoints the server exposes via POST.
POST_PATHS = {
    "search",
    "smart-search",
    "graph-query",
    "graph-stats",
    # Slash-form REST routes the viewer bundle actually calls (the daemon
    # registers both spellings; the Graph tab POSTs queries with a body and
    # was 403-rejected when only the hyphen form was whitelisted).
    "graph/query",
    "graph/stats",
    "lesson-search",
    "lesson-list",
    "facet-query",
    "facet-get",
    "facet-stats",
    "facet-dimensions",
    "relations",
    "relations-list",
    "timeline",
    "sessions",
    "replay/sessions",
    "replay/load",
    "context",
    "working-context",
    "insight-search",
    "insight-list",
    "semantic",
    "semantic-list",
    "procedural",
    "procedural-list",
    "patterns",
    "next",
    "frontier",
    "file-context",
    "crystal-list",
    "crystal-get",
    "action-list",
    "action-get",
    "audit",
    "profile",
    "config/flags",
    "config-flags",
    "verify",
    "diagnose",
}


def _target_base() -> str:
    override = os.environ.get("AGENTMEMORY_URL")
    if override:
        return override.rstrip("/")
    try:
        from helpers import plugins

        config = plugins.get_plugin_config("agentmemory") or {}
        url = str(config.get("url") or "").strip()
        if url:
            return url.rstrip("/")
    except Exception:
        pass
    return DEFAULT_TARGET


class Passthrough(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> Response:
        path = (request.args.get("path") or "").strip("/")
        method = request.method.upper()

        # Defensive normalization: some callers URL-encode the whole original
        # request (path + query) into the path parameter. Split any query
        # portion off so whitelist matching sees a clean endpoint name.
        embedded_query = ""
        if "?" in path:
            path, embedded_query = path.split("?", 1)

        if not path:
            return self._json_error("missing path parameter", 400)
        if method == "GET" and path not in GET_PATHS:
            return self._json_error(f"GET path not allowed: {path}", 403)
        if method == "POST" and path not in POST_PATHS:
            return self._json_error(f"POST path not allowed: {path}", 403)

        # Rebuild the query string minus our own path parameter, and forward
        # all other query args verbatim (sessionId, limit, cursor, ...).
        args = {k: v for k, v in request.args.items(multi=False) if k != "path"}
        if embedded_query:
            for pair in embedded_query.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    args.setdefault(urllib.parse.unquote_plus(k), urllib.parse.unquote_plus(v))
        url = f"{_target_base()}/agentmemory/{path}"
        if args:
            url += "?" + urllib.parse.urlencode(args)

        body = None
        headers = {"Accept": "application/json"}
        if method == "POST":
            body = json.dumps(input if isinstance(input, dict) and input else {}).encode("utf-8")
            headers["Content-Type"] = "application/json"

        proxy_request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(proxy_request, timeout=TIMEOUT_SECONDS) as response:
                payload = response.read()
                return Response(
                    payload,
                    status=response.status,
                    content_type=response.headers.get("Content-Type", "application/json"),
                )
        except urllib.error.HTTPError as exc:
            return Response(
                exc.read(),
                status=exc.code,
                content_type=exc.headers.get("Content-Type", "application/json"),
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return self._json_error(
                f"AgentMemory unreachable: {exc}",
                502,
                hint="start it with: npx -y @agentmemory/agentmemory (in the container)",
            )

    @staticmethod
    def _json_error(message: str, status: int, hint: str = "") -> Response:
        payload = {"error": message}
        if hint:
            payload["hint"] = hint
        return Response(json.dumps(payload), status=status, content_type="application/json")

"""AgentMemory API proxy for the WebUI Memory panel.

Forwards read-only panel requests to the AgentMemory server running in the
Agent Zero container (default http://localhost:3111). The panel fetches
through this handler so the user's browser never needs direct access to
container-local ports.

Security: GET endpoints are whitelisted (health, memories, sessions,
observations); POST is whitelisted to search only. The panel is a viewer —
no write endpoints are exposed. Every call needs an authenticated WebUI
session with a valid CSRF token (ApiHandler defaults).
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
TIMEOUT_SECONDS = 10

GET_PATHS = {"health", "memories", "sessions", "observations"}
POST_PATHS = {"search"}


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


class Proxy(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> Response:
        path = (request.args.get("path") or "").strip("/")
        method = request.method.upper()

        if not path:
            return self._json_error("missing path parameter", 400)
        if method == "GET" and path not in GET_PATHS:
            return self._json_error(f"GET path not allowed: {path}", 403)
        if method == "POST" and path not in POST_PATHS:
            return self._json_error(f"POST path not allowed: {path}", 403)

        url = f"{_target_base()}/agentmemory/{path}"
        if method == "GET" and path == "observations":
            session_id = (request.args.get("sessionId") or "").strip()
            if not session_id:
                return self._json_error("sessionId required", 400)
            url += f"?sessionId={urllib.parse.quote(session_id)}"

        body = None
        headers = {"Accept": "application/json"}
        if method == "POST":
            body = json.dumps(input.get("body") or {}).encode("utf-8")
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

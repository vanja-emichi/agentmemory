"""Auto-start manager for a container-local AgentMemory server.

ensure_server() checks the configured URL's health and, when the URL points
at this container (localhost/127.0.0.1/[::1]), spawns the server detached so
it survives the framework process. Remote URLs are never spawned. A module
lock prevents double-spawning from concurrent hooks/threads.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from usr.plugins.agentmemory.helpers import client


def _framework_root() -> Path:
    """Locate the Agent Zero framework root (dir holding plugins/ + usr/)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "plugins").is_dir() and (parent / "usr").is_dir():
            return parent
    return Path("/a0")


def _llm_env_from_utility_model() -> dict:
    """Resolve the user's configured Agent Zero utility model into
    AgentMemory daemon env vars.

    Resolution order (first that yields a provider + key wins):
      1. The ``_model_config`` plugin's utility model (whatever provider
         the user picked in Settings), including its api_base from
         ``conf/model_providers.yaml`` and its API key resolved through
         ``models.get_api_key``.
      2. Legacy fallback to the a0_venice env key (older deployments).
      3. Nothing — the daemon then runs zero-LLM (BM25 + local
         embeddings) rather than with a hardcoded key.

    Returns a dict of agentmemory env vars (OPENAI_*/ANTHROPIC_*/...).
    Never raises: background callers depend on this.
    """
    env: dict = {}
    try:
        import sys

        root = str(_framework_root())
        if root not in sys.path:
            sys.path.insert(0, root)

        from plugins._model_config.helpers.model_config import (
            get_utility_model_config,
        )

        cfg = get_utility_model_config() or {}
        provider = str(cfg.get("provider") or "").strip().strip('"')
        model = str(cfg.get("name") or "").strip().strip('"')
        if provider and model:
            api_key = ""
            api_base = str(cfg.get("api_base") or "").strip()
            litellm_provider = ""
            try:
                import models as a0_models

                api_key = str(a0_models.get_api_key(provider) or "").strip()
                if api_key.lower() == "none":
                    api_key = ""
            except Exception:
                api_key = ""
            try:
                import yaml

                providers_yaml = _framework_root() / "conf" / "model_providers.yaml"
                with open(providers_yaml, "r", encoding="utf-8") as handle:
                    providers_cfg = yaml.safe_load(handle) or {}
                entry = (providers_cfg.get("chat") or {}).get(provider) or {}
                litellm_provider = str(entry.get("litellm_provider") or "").strip().lower()
                if not api_base:
                    api_base = str((entry.get("kwargs") or {}).get("api_base") or "").strip()
            except Exception:
                pass

            if api_key:
                kind = litellm_provider or "openai"
                if kind == "anthropic":
                    env["ANTHROPIC_API_KEY"] = api_key
                    env["ANTHROPIC_MODEL"] = model
                    if api_base:
                        env["ANTHROPIC_BASE_URL"] = api_base
                elif kind == "gemini":
                    env["GEMINI_API_KEY"] = api_key
                    env["GEMINI_MODEL"] = model
                elif kind == "openrouter":
                    env["OPENROUTER_API_KEY"] = api_key
                    env["OPENROUTER_MODEL"] = model
                else:
                    # OpenAI-compatible (covers a0_venice, deepseek, vllm...)
                    env["OPENAI_API_KEY"] = api_key
                    env["OPENAI_MODEL"] = model
                    if api_base:
                        env["OPENAI_BASE_URL"] = api_base
    except Exception:
        env = {}

    if not env:
        # Legacy fallback for deployments predating _model_config.
        legacy_key = os.environ.get("API_KEY_A0_VENICE", "").strip()
        if legacy_key:
            env["OPENAI_API_KEY"] = legacy_key
            env["OPENAI_BASE_URL"] = "https://llm.agent-zero.ai/v1"
            env["OPENAI_MODEL"] = "deepseek-v4-flash-0731"
    return env

_LOCK = threading.Lock()

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
HEALTH_TIMEOUT = 2.0
SPAWN_WAIT_SECONDS = 45
POLL_INTERVAL = 1.0


def _is_local_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in LOCAL_HOSTS


def _health_ok(url: str) -> bool:
    try:
        request = urllib.request.Request(
            f"{url.rstrip('/')}/agentmemory/health", method="GET"
        )
        with urllib.request.urlopen(request, timeout=HEALTH_TIMEOUT) as response:
            return response.status == 200
    except Exception:
        return False


def _spawn(workdir: str) -> bool:
    npx = shutil.which("npx") or "npx"
    try:
        os.makedirs(workdir, exist_ok=True)
        log_path = os.path.join(workdir, "agentmemory.log")
        env = os.environ.copy()
        env["PATH"] = "/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
        # Route the summarizer/compressor LLM to the user's configured
        # Agent Zero utility model (whatever provider they chose in
        # Settings). setdefault so explicit config in the daemon's
        # environment always wins.
        for key, value in _llm_env_from_utility_model().items():
            env.setdefault(key, value)
        # Keep embeddings on-device; the gateway is for chat completions.
        env.setdefault("EMBEDDING_PROVIDER", "local")
        # Feature flags (all default OFF upstream). The daemon also reads
        # ~/.agentmemory/.env at boot, but .env is per-box config — carrying
        # the flags on spawn keeps A0 deployments self-contained.
        env.setdefault("GRAPH_EXTRACTION_ENABLED", "true")
        env.setdefault("AGENTMEMORY_AUTO_COMPRESS", "true")
        env.setdefault("AGENTMEMORY_INJECT_CONTEXT", "true")
        # Second-wave automation flags (verified against upstream design):
        # pinned memory slots, slot reflection on session end (auto lesson
        # synthesis), and the local MiniLM reranker (zero LLM cost).
        env.setdefault("AGENTMEMORY_SLOTS", "true")
        env.setdefault("AGENTMEMORY_REFLECT", "true")
        env.setdefault("RERANK_ENABLED", "true")
        # LLM timeout headroom: consolidation prompts are large and the 60s
        # upstream default intermittently times out on slower providers
        # (22 semantic-consolidation failures observed against z.ai glm-5.2).
        env.setdefault("AGENTMEMORY_LLM_TIMEOUT_MS", "120000")
        # Tier 3: team memory (share/feed/profile). Disabled upstream by
        # default; enabled so A0 subordinates can share discoveries.
        env.setdefault("TEAM_MODE", "shared")
        env.setdefault("TEAM_ID", "a0-team")
        env.setdefault("USER_ID", "a0")
        # V8 heap headroom: under load the daemon self-reports
        # memory_heap_tight (~87% of the ~64 MB default old-space) while
        # RSS sits near 300 MB — OOM risk during graph/compress bursts.
        # 512 MB keeps GC comfortable; appended (not setdefault) so an
        # operator's own NODE_OPTIONS flags survive untouched.
        node_options = env.get("NODE_OPTIONS", "")
        if "--max-old-space-size" not in node_options:
            env["NODE_OPTIONS"] = (node_options + " --max-old-space-size=512").strip()
        with open(log_path, "ab") as log:
            subprocess.Popen(
                [npx, "-y", "@agentmemory/agentmemory"],
                cwd=workdir,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                env=env,
                start_new_session=True,
            )
        return True
    except Exception as error:
        print(f"[agentmemory] auto-start failed: {error}")
        return False


def ensure_server(agent=None) -> bool:
    """Return True when the server is (or becomes) healthy.

    Never raises: callers run this in fire-and-forget daemon threads.
    """
    try:
        config = client.get_config(agent)
        if not config.get("enabled", True) or not config.get("auto_start", True):
            return False
        url = str(config.get("url") or "")
        if not url:
            return False
        if _health_ok(url):
            return True
        if not _is_local_url(url):
            return False  # remote server: never spawn

        with _LOCK:
            if _health_ok(url):  # re-check under lock
                return True
            from helpers import settings as a0_settings

            workdir = a0_settings.get_settings().get("workdir_path") or "/a0/usr/workdir"
            if not _spawn(workdir):
                return False
            deadline = time.monotonic() + SPAWN_WAIT_SECONDS
            while time.monotonic() < deadline:
                if _health_ok(url):
                    print("[agentmemory] server auto-started: " + url)
                    return True
                time.sleep(POLL_INTERVAL)
            print("[agentmemory] server did not become healthy in time: " + url)
            return False
    except Exception as error:
        print(f"[agentmemory] ensure_server error: {error}")
        return False

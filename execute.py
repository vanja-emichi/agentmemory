#!/usr/bin/env python3
"""AgentMemory plugin setup / health-check action.

Runs when the user presses Execute in the Agent Zero Plugin list.
Contract: plain script executed with the framework Python, cwd set to
this plugin directory, stdout captured into the UI, 120s budget,
exit code 0 = success. Does three things:

  1. Resolves the user's Agent Zero utility model into daemon env vars
     (no hardcoded keys anywhere).
  2. Ensures the container-local AgentMemory daemon is running
     (spawns or revives it with the full automation flag set).
  3. Verifies health, provider, feature flags and search indexes,
     printing a green/red report.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path


def _bootstrap() -> Path:
    """Make framework + plugin importable; return framework root."""
    plugin_root = Path(__file__).resolve().parent
    for parent in plugin_root.parents:
        if (parent / "plugins").is_dir() and (parent / "usr").is_dir():
            root = parent
            break
    else:
        root = Path("/a0")
    for path in (str(root), str(plugin_root)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return root


ROOT = _bootstrap()


def _get_json(url: str, timeout: float = 8.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), True
    except Exception as exc:  # noqa: BLE001 - report, never crash
        return {"error": str(exc)}, False


def main() -> int:
    print("AgentMemory plugin — setup & health check")
    print("=" * 46)

    failures = 0

    # ---- 1. Utility model resolution ---------------------------------
    try:
        from usr.plugins.agentmemory.helpers import server_manager

        llm_env = server_manager._llm_env_from_utility_model()
    except Exception as exc:  # noqa: BLE001
        llm_env = {}
        print(f"[FAIL] utility model resolver: {exc}")
        failures += 1

    if llm_env:
        model = llm_env.get("OPENAI_MODEL") or llm_env.get("ANTHROPIC_MODEL") \
            or llm_env.get("GEMINI_MODEL") or llm_env.get("OPENROUTER_MODEL") or "?"
        base = llm_env.get("OPENAI_BASE_URL") or llm_env.get("ANTHROPIC_BASE_URL") or "(default)"
        print(f"[ OK ] Utility model wired: {model}")
        print(f"        via {base}")
    else:
        print("[WARN] No utility model/key resolved — daemon runs zero-LLM")
        print("        (BM25 + local embeddings). Configure a utility model")
        print("        in Settings → Models, then Execute again.")

    # ---- 2. Daemon ensure --------------------------------------------
    try:
        from usr.plugins.agentmemory.helpers import client as am_client

        config = am_client.get_config(None)
    except Exception:
        config = {}
    base_url = str(config.get("url") or "http://localhost:3111").rstrip("/")

    _, ok = _get_json(f"{base_url}/agentmemory/health", timeout=4)
    if not ok:
        print("[ .. ] Daemon down — spawning (full flag set, ~20-40s)")
        try:
            started = server_manager.ensure_server(None)
        except Exception as exc:  # noqa: BLE001
            started = False
            print(f"[FAIL] spawn error: {exc}")
        if started:
            print("[ OK ] Daemon started")
        else:
            print("[FAIL] Daemon did not become healthy (see workdir/agentmemory.log)")
            failures += 1
    else:
        print("[ OK ] Daemon already running")

    health, ok = _get_json(f"{base_url}/agentmemory/health")
    if ok:
        status = health.get("status")
        workers = len(health.get("health", {}).get("workers", []))
        print(f"[ OK ] Health: {status} ({workers} worker)")
        provider = health.get("provider", "?")
        print(f"[ OK ] LLM provider kind: {provider}")
        metrics = health.get("functionMetrics") or []
        for m in metrics:
            print(
                f"        {m.get('functionId')}: {m.get('successCount', 0)} ok /"
                f" {m.get('failureCount', 0)} failed"
                f" (avg quality {m.get('avgQualityScore', 0)})"
            )
    else:
        failures += 1

    # ---- 3. Feature flags --------------------------------------------
    flags, ok = _get_json(f"{base_url}/agentmemory/config/flags")
    if ok:
        expected = {
            "GRAPH_EXTRACTION_ENABLED",
            "CONSOLIDATION_ENABLED",
            "AGENTMEMORY_AUTO_COMPRESS",
            "AGENTMEMORY_INJECT_CONTEXT",
        }
        for flag in flags.get("flags", []):
            key = flag.get("key")
            state = flag.get("enabled")
            mark = " OK " if state else ("WARN" if key in expected else "info")
            print(f"[{mark}] flag {key} = {str(state).lower()}")
            if key in expected and not state:
                print("        (this flag should be true after a spawn with")
                print("         the plugin's server_manager — restart daemon)")
    else:
        print("[FAIL] could not read config/flags")
        failures += 1

    # ---- 4. Data sanity ----------------------------------------------
    stats, ok = _get_json(f"{base_url}/agentmemory/graph/stats")
    if ok:
        nodes = stats.get("totalNodes", 0)
        edges = stats.get("totalEdges", 0)
        print(f"[ OK ] Knowledge graph: {nodes} nodes / {edges} edges")
        if nodes == 0 and llm_env:
            print("        (graph empty — extraction will fill it as sessions")
            print("         run; or POST /agentmemory/graph/build to backfill)")

    # ---- Summary ------------------------------------------------------
    print("=" * 46)
    if failures:
        print(f"RESULT: {failures} failure(s). Check workdir/agentmemory.log")
        return 1
    print("RESULT: AgentMemory is set up and healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

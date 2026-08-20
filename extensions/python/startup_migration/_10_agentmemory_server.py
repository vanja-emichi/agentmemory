from __future__ import annotations

import threading

from helpers.extension import Extension

from usr.plugins.agentmemory.helpers import server_manager


class AgentMemoryServerBoot(Extension):
    """Starts a container-local AgentMemory server at framework boot.

    Runs detached in a daemon thread so boot never blocks; the server itself
    is spawned with start_new_session=True and outlives this process.
    """

    def execute(self, **kwargs):
        threading.Thread(
            target=server_manager.ensure_server,
            name="a0-agentmemory-server-boot",
            daemon=True,
        ).start()

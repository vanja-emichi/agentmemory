from helpers.extension import Extension
from agent import LoopData

from usr.plugins.agentmemory.helpers import client


class AgentMemorySession(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        config = client.get_config(self.agent)
        if not config["enabled"] or not (config["auto_recall"] or config["auto_capture"]):
            return

        session_number = int(self.agent.get_data("agentmemory_session_number") or 0) + 1
        self.agent.set_data("agentmemory_session_number", session_number)
        self.agent.set_data(
            client.SESSION_ID_KEY,
            f"{self.agent.context.id}:{session_number}",
        )

        if not self.agent.get_data("agentmemory_boot_started"):
            self.agent.set_data("agentmemory_boot_started", True)
            import threading
            from usr.plugins.agentmemory.helpers import server_manager
            threading.Thread(
                target=server_manager.ensure_server,
                args=(self.agent,),
                name="a0-agentmemory-server-heal",
                daemon=True,
            ).start()

        title = loop_data.user_message.output_text() if loop_data.user_message else ""
        try:
            result = await client.start_session(self.agent, title)
            if config["auto_recall"] and result.get("context"):
                loop_data.extras_temporary["agentmemory_context"] = self.agent.read_prompt(
                    "agent.extras.agentmemory_context.md",
                    context=result["context"],
                )
                # Surface pending cross-session work so the agent can
                # proactively propose continuing it (propose, never start
                # work without user confirmation).
                try:
                    frontier = await client.frontier(self.agent, limit=5)
                    entries = frontier.get("frontier") or []
                    if entries:
                        lines = ["## AgentMemory pending actions (frontier)"]
                        lines.append(
                            "Open cross-session work items exist. Mention the "
                            "most relevant ones when proposing next steps; "
                            "propose, do not start them without user approval."
                        )
                        for entry in entries:
                            action = entry.get("action") or {}
                            lines.append(
                                f"- p{action.get('priority', '?')} "
                                f"{action.get('title', '?')} (id: {action.get('id', '?')})"
                            )
                        loop_data.extras_temporary["agentmemory_actions"] = "\n".join(lines)
                except Exception:
                    pass
            if config["auto_capture"] and title.strip():
                await client.observe(
                    self.agent,
                    "prompt_submit",
                    {"prompt": title[:12000]},
                )
        except client.AgentMemoryError:
            self.agent.set_data("agentmemory_last_error", True)

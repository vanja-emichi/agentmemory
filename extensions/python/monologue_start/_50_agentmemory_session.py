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

        title = loop_data.user_message.output_text() if loop_data.user_message else ""
        try:
            result = await client.start_session(self.agent, title)
            if config["auto_recall"] and result.get("context"):
                loop_data.extras_temporary["agentmemory_context"] = self.agent.read_prompt(
                    "agent.extras.agentmemory_context.md",
                    context=result["context"],
                )
            if config["auto_capture"] and title.strip():
                await client.observe(
                    self.agent,
                    "prompt_submit",
                    {"prompt": title[:12000]},
                )
        except client.AgentMemoryError:
            self.agent.set_data("agentmemory_last_error", True)

from helpers.extension import Extension
from helpers.tool import Response

from usr.plugins.agentmemory.helpers import client


class AgentMemoryObserve(Extension):
    async def execute(
        self,
        response: Response | None = None,
        tool_name: str = "",
        **kwargs,
    ):
        if not self.agent or not response or not tool_name:
            return
        config = client.get_config(self.agent)
        if not config["enabled"] or not config["auto_capture"]:
            return
        if tool_name.startswith("agentmemory_"):
            return
        try:
            await client.observe(
                self.agent,
                "post_tool_use",
                {
                    "tool_name": tool_name,
                    "tool_output": response.message[:8000],
                },
            )
        except client.AgentMemoryError:
            return

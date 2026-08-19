from helpers.extension import Extension
from agent import LoopData

from usr.plugins.agentmemory.helpers import client


class AgentMemorySessionEnd(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent or not self.agent.get_data(client.SESSION_ID_KEY):
            return
        if not client.get_config(self.agent)["enabled"]:
            return
        try:
            await client.end_session(self.agent)
        except client.AgentMemoryError:
            return

import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    team_feed,
    team_profile,
    team_share,
)


class AgentMemoryTeam(Tool):
    """Team memory: share, feed, profile."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "share": self._share,
            "feed": self._feed,
            "profile": self._profile,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _share(self, item_id="", item_type="", **kwargs):
        item_id = str(item_id or "").strip()
        item_type = str(item_type or "").strip().lower()
        if not item_id:
            return Response("Error: item_id is required", break_loop=False)
        if item_type not in {"observation", "memory", "pattern"}:
            return Response(
                "Error: item_type must be one of observation, memory, pattern",
                break_loop=False,
            )
        try:
            result = await team_share(self.agent, item_id, item_type)
        except AgentMemoryError as error:
            return Response(f"AgentMemory team share failed: {error}", break_loop=False)
        item = result.get("item") or result
        return Response(
            json.dumps(
                {
                    "shared": True,
                    "itemId": item.get("id", item_id),
                    "type": item.get("type", item_type),
                    "sharedBy": item.get("sharedBy"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _feed(self, limit=20, **kwargs):
        try:
            result = await team_feed(
                self.agent, int(limit) if str(limit).strip().isdigit() else 20
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory team feed failed: {error}", break_loop=False)
        items = result.get("items") or result.get("feed") or []
        lines = [f"{len(items)} shared item(s):"]
        for item in items:
            lines.append(
                f"- [{item.get('type', '?')}] {item.get('sharedBy', '?')}: "
                f"{str(item.get('content'))[:120]} ({item.get('id')})"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _profile(self, agent_id="", **kwargs):
        try:
            result = await team_profile(self.agent, str(agent_id or "").strip())
        except AgentMemoryError as error:
            return Response(f"AgentMemory team profile failed: {error}", break_loop=False)
        profile = result.get("profile") or result
        if not profile:
            return Response("No team profile available yet.", break_loop=False)
        members = ", ".join(profile.get("members") or []) or "none"
        concepts = ", ".join(
            str(entry.get("concept"))
            for entry in (profile.get("topConcepts") or [])[:5]
        )
        lines = [
            f"Team: {profile.get('teamId', '?')} (members: {members})",
            f"Shared items: {profile.get('totalSharedItems', 0)}",
        ]
        if concepts:
            lines.append(f"Top concepts: {concepts}")
        return Response("\n".join(lines), break_loop=False)

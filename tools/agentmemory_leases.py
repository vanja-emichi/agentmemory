import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    default_agent_id,
    lease_acquire,
    lease_release,
    lease_renew,
)


class AgentMemoryLeases(Tool):
    """Exclusive action leases: acquire, renew, release."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "acquire": self._acquire,
            "renew": self._renew,
            "release": self._release,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    def _identity(self, agent_id: str) -> str:
        return str(agent_id or "").strip() or default_agent_id(self.agent)

    async def _acquire(self, action_id="", agent_id="", ttl_seconds=600, **kwargs):
        action_id = str(action_id or "").strip()
        if not action_id:
            return Response("Error: action_id is required", break_loop=False)
        try:
            result = await lease_acquire(
                self.agent,
                action_id,
                self._identity(agent_id),
                int(ttl_seconds) if str(ttl_seconds).strip().isdigit() else 600,
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory lease acquire failed: {error}", break_loop=False)
        lease = result.get("lease") or result
        acquired = bool(lease.get("id"))
        body: dict = {
            "acquired": acquired,
            "leaseId": lease.get("id"),
            "actionId": lease.get("actionId"),
            "agentId": lease.get("agentId"),
            "expiresAt": lease.get("expiresAt"),
            "status": lease.get("status"),
        }
        if not acquired:
            body["hint"] = (
                "acquire failed — the action may already be leased by another "
                "agent, completed, or missing; check the action status or use "
                "a different action"
            )
            if result.get("error"):
                body["serverError"] = result.get("error")
        return Response(
            json.dumps(body, indent=2, ensure_ascii=False), break_loop=False
        )

    async def _renew(self, action_id="", agent_id="", ttl_seconds=600, **kwargs):
        action_id = str(action_id or "").strip()
        if not action_id:
            return Response("Error: action_id is required", break_loop=False)
        try:
            result = await lease_renew(
                self.agent,
                action_id,
                self._identity(agent_id),
                int(ttl_seconds) if str(ttl_seconds).strip().isdigit() else 600,
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory lease renew failed: {error}", break_loop=False)
        lease = result.get("lease") or result
        renewed = bool(lease.get("expiresAt"))
        body: dict = {
            "renewed": renewed,
            "leaseId": lease.get("id"),
            "expiresAt": lease.get("expiresAt"),
        }
        if not renewed:
            body["hint"] = (
                "renewal did not extend a lease — only the lease holder can "
                "renew; verify you acquired it with the same agent_id"
            )
        return Response(
            json.dumps(body, indent=2, ensure_ascii=False), break_loop=False
        )

    async def _release(self, action_id="", agent_id="", result="", **kwargs):
        action_id = str(action_id or "").strip()
        if not action_id:
            return Response("Error: action_id is required", break_loop=False)
        try:
            outcome = await lease_release(
                self.agent, action_id, self._identity(agent_id), str(result or "")
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory lease release failed: {error}", break_loop=False)
        return Response(
            json.dumps(
                {"released": bool(outcome.get("released")), "actionId": action_id},
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    default_agent_id,
    signal_read,
    signal_send,
    signal_threads,
)


class AgentMemorySignals(Tool):
    """Inter-agent signals: send, read, threads."""
    # D11: declared native function-calling schema (schema source-of-truth).
    native_schema = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "description": "Operation to perform. One of: read, send, threads.",
            "enum": [
                "read",
                "send",
                "threads"
            ]
        },
        "content": {
            "type": "string"
        },
        "to": {
            "type": "string"
        },
        "type": {
            "type": "string"
        },
        "reply_to": {
            "type": "string"
        },
        "agent_id": {
            "type": "string"
        },
        "unread_only": {
            "type": "boolean"
        },
        "thread_id": {
            "type": "string"
        },
        "limit": {
            "type": "integer"
        }
    },
    "additionalProperties": True
}


    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "send": self._send,
            "read": self._read,
            "threads": self._threads,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _send(self, content="", to="", type="", reply_to="", **kwargs):
        content = str(content or "").strip()
        if not content:
            return Response("Error: content is required", break_loop=False)
        sender = str(kwargs.get("from") or "").strip() or default_agent_id(self.agent)
        try:
            result = await signal_send(
                self.agent,
                sender,
                content,
                str(to or ""),
                str(type or ""),
                str(reply_to or ""),
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory signal send failed: {error}", break_loop=False)
        signal = result.get("signal") or result
        return Response(
            json.dumps(
                {
                    "sent": True,
                    "signalId": signal.get("id"),
                    "threadId": signal.get("threadId"),
                    "from": signal.get("from"),
                    "to": signal.get("to"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _read(self, agent_id="", unread_only=False, thread_id="", limit=50, **kwargs):
        recipient = str(agent_id or "").strip() or default_agent_id(self.agent)
        try:
            result = await signal_read(
                self.agent,
                recipient,
                bool(unread_only),
                str(thread_id or ""),
                int(limit) if str(limit).strip().isdigit() else 50,
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory signal read failed: {error}", break_loop=False)
        signals = result.get("signals") or []
        lines = [f"{len(signals)} signal(s) for '{recipient}'"]
        for signal in signals:
            read = "read" if signal.get("readAt") else "unread"
            lines.append(
                f"- [{signal.get('type', 'info')}/{read}] {signal.get('from')} -> "
                f"{signal.get('to') or 'broadcast'}: "
                f"{str(signal.get('content'))[:200]} ({signal.get('id')})"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _threads(self, agent_id="", **kwargs):
        owner = str(agent_id or "").strip() or default_agent_id(self.agent)
        try:
            result = await signal_threads(self.agent, owner)
        except AgentMemoryError as error:
            return Response(f"AgentMemory signal threads failed: {error}", break_loop=False)
        return Response(
            json.dumps(result, indent=2, ensure_ascii=False), break_loop=False
        )

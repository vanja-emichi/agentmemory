import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    relation_create,
    relations_list,
)


RELATION_TYPES = ("supersedes", "extends", "derives", "contradicts", "related")


class AgentMemoryRelations(Tool):
    """Memory relations: relate two memories, list relations."""

    # D11: declared native function-calling schema (schema source-of-truth).
    native_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Operation to perform. One of: list, relate.",
                "enum": ["list", "relate"],
            },
            "source_id": {
                "type": "string",
                "description": "Memory id of the relation source (relate only; usually the newer memory).",
            },
            "target_id": {
                "type": "string",
                "description": "Memory id of the relation target (relate only; usually the older memory).",
            },
            "relation_type": {
                "type": "string",
                "description": "Relation kind (relate only).",
                "enum": list(RELATION_TYPES),
            },
            "confidence": {
                "type": "number",
                "description": "Optional confidence 0..1 (relate only; computed from shared sessions/age when omitted).",
            },
            "limit": {
                "type": "integer",
                "description": "Max relations to list (list only).",
            },
        },
        "required": ["operation"],
        "additionalProperties": True,
    }

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "list": self._list,
            "relate": self._relate,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _list(self, limit=50, **kwargs):
        try:
            result = await relations_list(
                self.agent, int(limit) if str(limit).strip().isdigit() else 50
            )
        except AgentMemoryError as error:
            return Response(
                f"AgentMemory relations list failed: {error}", break_loop=False
            )
        relations = result.get("relations") or []
        if not relations:
            return Response(
                "No relations yet. Create one with operation 'relate'.",
                break_loop=False,
            )
        lines = [f"{len(relations)} relation(s):"]
        for rel in relations:
            lines.append(
                f"- {rel.get('sourceId')} --[{rel.get('type')}]--> "
                f"{rel.get('targetId')} (confidence {rel.get('confidence')})"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _relate(
        self, source_id="", target_id="", relation_type="", confidence=None, **kwargs
    ):
        source_id = str(source_id or "").strip()
        target_id = str(target_id or "").strip()
        relation_type = str(relation_type or "").strip().lower()
        if not source_id or not target_id:
            return Response(
                "Error: source_id and target_id are required",
                break_loop=False,
            )
        if relation_type not in RELATION_TYPES:
            return Response(
                f"Error: relation_type must be one of {', '.join(RELATION_TYPES)}",
                break_loop=False,
            )
        conf = None
        if str(confidence or "").strip():
            try:
                conf = float(confidence)
            except (TypeError, ValueError):
                conf = None
        try:
            result = await relation_create(
                self.agent, source_id, target_id, relation_type, conf
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory relate failed: {error}", break_loop=False)
        return Response(
            json.dumps(result, indent=2, ensure_ascii=False), break_loop=False
        )

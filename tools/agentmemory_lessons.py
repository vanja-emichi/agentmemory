import json

from helpers.tool import Response, Tool
from usr.plugins.agentmemory.helpers.client import (
    AgentMemoryError,
    lesson_delete,
    lesson_save,
    lesson_search,
)


class AgentMemoryLessons(Tool):
    """Consult and manage AgentMemory lessons: confidence-weighted rules
    derived from corrections, crystals, and recurring patterns."""

    async def execute(self, operation="", **kwargs):
        operation = str(operation or "").strip().lower()
        handlers = {
            "recall": self._recall,
            "save": self._save,
            "delete": self._delete,
        }
        handler = handlers.get(operation)
        if not handler:
            return Response(
                f"Error: unknown operation '{operation}'. "
                f"Valid: {', '.join(sorted(handlers))}.",
                break_loop=False,
            )
        return await handler(**kwargs)

    async def _recall(self, query="", limit=10, **kwargs):
        query = str(query or "").strip()
        if not query:
            return Response("Error: query is required", break_loop=False)
        try:
            result = await lesson_search(self.agent, query, _as_int(limit, 10))
        except AgentMemoryError as error:
            return Response(f"AgentMemory lesson recall failed: {error}", break_loop=False)
        lessons = result.get("lessons") or []
        lines = [f"{len(lessons)} lesson(s):"]
        for lesson in lessons:
            lines.append(
                f"- [{lesson.get('confidence', '?')}] "
                f"{str(lesson.get('content') or '')[:160]}"
            )
        return Response("\n".join(lines), break_loop=False)

    async def _save(self, content="", context="", confidence=0.6, **kwargs):
        content = str(content or "").strip()
        if not content:
            return Response("Error: content is required", break_loop=False)
        try:
            result = await lesson_save(
                self.agent,
                content,
                str(context or ""),
                _as_float(confidence, 0.6),
            )
        except AgentMemoryError as error:
            return Response(f"AgentMemory lesson save failed: {error}", break_loop=False)
        lesson = result.get("lesson") or {}
        return Response(
            json.dumps(
                {
                    "saved": True,
                    "id": lesson.get("id"),
                    "confidence": lesson.get("confidence"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            break_loop=False,
        )

    async def _delete(self, lesson_id="", **kwargs):
        lesson_id = str(lesson_id or "").strip()
        if not lesson_id:
            return Response("Error: lesson_id is required", break_loop=False)
        try:
            result = await lesson_delete(self.agent, lesson_id)
        except AgentMemoryError as error:
            return Response(f"AgentMemory lesson delete failed: {error}", break_loop=False)
        return Response(
            json.dumps(result, indent=2, ensure_ascii=False), break_loop=False
        )


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

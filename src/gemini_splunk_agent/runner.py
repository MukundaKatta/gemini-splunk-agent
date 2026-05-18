"""Programmatic agent invocation. Wraps ADK's Runner so the Streamlit
dashboard can fire off agent calls without touching the `adk web` CLI.

Also wires every Gemini call through GeminiLens for self-observation:
the same library we publish elsewhere is used to record traces for the
agent itself."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gemini_splunk_agent.agent import build_agent

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    _ADK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ADK_AVAILABLE = False


@dataclass
class AgentResponse:
    final_text: str
    events: list[dict[str, Any]]
    trace_id: str | None = None
    error: str | None = None


def _observer():
    """Return a GeminiObserver bound to a per-process trace store if the
    geminilens library is importable, else None. Optional dep."""
    try:
        from geminilens import GeminiObserver, TraceStore
    except ImportError:
        return None
    store = TraceStore(Path.home() / ".gemini-splunk-agent" / "traces.jsonl")
    return GeminiObserver(store=store, default_tags={"agent": "gemini_splunk_agent"})


async def _ainvoke(question: str, *, stub: bool, model: str) -> AgentResponse:
    agent = build_agent(model=model, stub=stub)
    if agent is None or not _ADK_AVAILABLE:
        return AgentResponse(
            final_text=(
                "(offline-fallback) google-adk is not installed in this environment. "
                "Install with: pip install google-adk mcp"
            ),
            events=[],
            error="ADK not available",
        )

    session_service = InMemorySessionService()
    app_name = "gemini-splunk-agent"
    user_id = os.getenv("USER", "demo")
    session = await session_service.create_session(app_name=app_name, user_id=user_id)
    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

    content = types.Content(role="user", parts=[types.Part(text=question)])
    events: list[dict[str, Any]] = []
    final_text = ""

    obs = _observer()
    trace_cm = obs.trace(model=model, prompt=question, scenario="ops-investigation") if obs else None
    if trace_cm is not None:
        trace_cm.__enter__()  # async context not needed; trace is a sync CM

    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=content
        ):
            ev_dict = {
                "author": getattr(event, "author", None),
                "is_final": event.is_final_response() if hasattr(event, "is_final_response") else False,
            }
            if hasattr(event, "content") and event.content is not None:
                parts = getattr(event.content, "parts", []) or []
                ev_dict["text"] = "".join(getattr(p, "text", "") or "" for p in parts)
                if ev_dict["is_final"]:
                    final_text = ev_dict["text"]
            events.append(ev_dict)
    finally:
        if trace_cm is not None:
            trace_cm.__exit__(None, None, None)

    return AgentResponse(final_text=final_text, events=events)


def ask(question: str, *, stub: bool = True, model: str = "gemini-2.5-flash") -> AgentResponse:
    """Synchronous wrapper around the async agent runner."""
    return asyncio.run(_ainvoke(question, stub=stub, model=model))

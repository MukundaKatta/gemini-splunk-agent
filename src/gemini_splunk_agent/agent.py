"""ADK Gemini agent wired to the Splunk MCP server.

Targets the Splunk Agentic Ops "Observability" track plus the "Best Use of
Splunk MCP Server" bonus prize. The McpToolset connection params point at
our local stub server by default (`gemini_splunk_agent.mcp_stub`). To
target a real Splunk Cloud / Enterprise instance, swap the params to the
official server (see below).
"""

from __future__ import annotations

import os
import sys
from typing import Any


try:
    from google.adk.agents import LlmAgent
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
    from mcp import StdioServerParameters
    _ADK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ADK_AVAILABLE = False


SYSTEM_PROMPT = """\
You are an SRE investigator on the Splunk platform. The user describes a
production symptom and you diagnose root cause using the Splunk tools you
have available — Splunk Enterprise indexes, saved-search alerts, and
Splunk Observability detectors.

Workflow you should follow:
1. Call `list_alerts` with status="active" to see what is currently firing.
2. For each firing alert, call `get_detector` with the detector_id to read
   the detector rule, current value, and baseline. Quote the rule verbatim.
3. Call `run_search` with the saved-search SPL attached to the alert to
   confirm the symptom in the underlying events. Cite specific timestamps,
   service names, p95 numbers, and host names from the result records.
4. Optionally, call `run_observability_query` to pull the underlying
   metric timeseries so the verdict has a graph, not just an alert summary.
5. Call `list_indexes` only when the user explicitly asks what data is
   on the cluster.

Final answer format — EXACTLY these labeled sections, in order:

ANSWER:        one sentence stating the firing alert + the root cause.
ACTIVE ALERT:  alert id + name + severity + status.
DETECTOR:      detector id + rule (verbatim) + current value vs baseline.
EVIDENCE:      2-4 bullets with SPL output lines, p95 numbers, timestamps.
                Quote everything verbatim from `run_search` / `run_observability_query`.
ROOT CAUSE:    one sentence grounded in the evidence above.
NEXT STEP:     one concrete action the on-call should take.

Strict rules: numbers, alert ids, detector ids, SPL fragments, and host names
must be copied verbatim from tool output. No fabricated values.
"""


def _splunk_toolset(stub: bool = True) -> Any:
    """Return an McpToolset bound to either the local stub server (default)
    or the real Splunk MCP server when stub=False."""
    if not _ADK_AVAILABLE:
        raise ImportError(
            "google-adk and mcp must be installed: pip install google-adk mcp"
        )

    if stub:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "gemini_splunk_agent.mcp_stub"],
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
            },
        )
    else:
        # Real Splunk MCP server (the official splunk/splunk-mcp package).
        # Set SPLUNK_HOST + SPLUNK_TOKEN for Enterprise + Observability.
        params = StdioServerParameters(
            command="npx",
            args=["-y", "@splunk/splunk-mcp"],
            env={
                **os.environ,
                "SPLUNK_HOST":       os.environ.get("SPLUNK_HOST", ""),
                "SPLUNK_TOKEN":      os.environ.get("SPLUNK_TOKEN", ""),
                "SPLUNK_O11Y_TOKEN": os.environ.get("SPLUNK_O11Y_TOKEN", ""),
            },
        )
    return McpToolset(connection_params=StdioConnectionParams(server_params=params))


def build_agent(model: str = "gemini-2.5-flash", stub: bool = True) -> Any:
    if not _ADK_AVAILABLE:
        return None
    return LlmAgent(
        model=model,
        name="gemini_splunk_agent",
        instruction=SYSTEM_PROMPT,
        tools=[_splunk_toolset(stub=stub)],
    )

# Architecture

```
                         ┌──────────────────────────────────┐
                         │  Streamlit dashboard on Cloud Run│
                         │  (app/dashboard.py)              │
                         └────────────┬─────────────────────┘
                                      │ ask()
                                      ▼
                         ┌──────────────────────────────────┐
                         │  runner.py · async ADK Runner    │
                         │  + GeminiLens trace recorder     │
                         └────────────┬─────────────────────┘
                                      │ run_async()
                                      ▼
       ┌────────────────────────────────────────────────────────────┐
       │  google.adk.agents.LlmAgent  (gemini-splunk-agent)          │
       │                                                              │
       │  Gemini 2.5 Flash via Vertex AI ── reasoning loop            │
       │  System prompt: forces labeled triage with verbatim quoting  │
       └─────────┬───────────────────────────────────────────────────┘
                 │ tool calls
                 ▼
       ┌─────────────────────────────────────────────────────────────┐
       │  McpToolset  →  StdioConnectionParams                        │
       │                                                                │
       │  stub=True  →  python -m gemini_splunk_agent.mcp_stub          │
       │                (5 tools, canned data, judge-reproducible)     │
       │                                                                │
       │  stub=False →  npx -y @splunk/splunk-mcp                       │
       │                (real Splunk Cloud + Observability)             │
       └─────────────────────────────────────────────────────────────┘
                 │ MCP stdio
                 ▼
       ┌─────────────────────────────────────────────────────────────┐
       │  Splunk MCP server tool surface (5 tools)                    │
       │                                                                │
       │  • list_alerts(status)               → fired alerts            │
       │  • get_detector(detector_id)         → rule + current/baseline │
       │  • list_indexes()                    → cluster manifest        │
       │  • run_search(spl)                   → SPL search job results  │
       │  • run_observability_query(metric)   → O11y metric timeseries  │
       └─────────────────────────────────────────────────────────────┘
                 │ (when stub=False)
                 ▼
       ┌─────────────────────────────────────────────────────────────┐
       │  Splunk Enterprise / Cloud  +  Splunk Observability Cloud    │
       │  via REST  /  Splunk's hosted MCP                            │
       └─────────────────────────────────────────────────────────────┘
```

## Components

- **Streamlit dashboard** (`app/dashboard.py`): user-facing UI on Cloud Run. Submits a symptom report, renders the labeled triage.
- **ADK Runner** (`src/gemini_splunk_agent/runner.py`): async wrapper that drives the agent. Wires every Gemini call through [GeminiLens](https://github.com/MukundaKatta/geminilens) for trace observability of the agent itself.
- **LlmAgent** (`src/gemini_splunk_agent/agent.py`): Gemini 2.5 Flash + a hardened system prompt that enforces labeled output sections (ANSWER / ACTIVE ALERT / DETECTOR / EVIDENCE / ROOT CAUSE / NEXT STEP) and verbatim tool-output quoting.
- **MCP toolset** (Splunk MCP server): the agent talks to either the bundled stub (default) or the official `@splunk/splunk-mcp` server when `stub=False`.

## Data flow

1. User asks "checkout-api latency spiked, what's broken?"
2. Agent calls `list_alerts(status="active")` → sees `ALRT-2026-0518-1432-A` firing.
3. Agent calls `get_detector("DTC-checkout-latency-p95")` → reads rule `p95(duration_ms) > 1500 over 15m`, current value 1842 ms, baseline 220 ms.
4. Agent calls `run_search(<saved-search SPL>)` → pulls 30 records, 218 ms pre-spike vs 1786 ms post-spike.
5. Agent calls `run_observability_query("checkout-api.duration_ms.p95")` → confirms the metric timeseries.
6. Agent emits the six-section triage with everything quoted verbatim.

## Why this matches Splunk Agentic Ops Observability track

- Production observability problem (checkout-api latency).
- Real Splunk surface (alerts + saved searches + Observability detectors + indexes).
- Splunk MCP server is the entire integration substrate — every tool call hits an MCP method.
- Output is auditable: each claim ties back to a specific tool call + verbatim identifier.

## Real-tenant deployment

Set `stub=False` in `agent.py` and provide:
- `SPLUNK_HOST` — Splunk Cloud or Enterprise endpoint
- `SPLUNK_TOKEN` — Splunk REST API token
- `SPLUNK_O11Y_TOKEN` — Splunk Observability Cloud access token

The stub's tool shape matches the real MCP server one-to-one, so the swap is configuration-only.

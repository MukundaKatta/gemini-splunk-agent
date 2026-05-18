# gemini-splunk-agent

A production-incident investigation agent built on **Google Cloud Agent
Builder (ADK)**, **Gemini 2.5**, and the **Splunk MCP server**.

**Live demo:** https://gemini-splunk-agent-1029931682737.us-central1.run.app
**Demo video:** https://storage.googleapis.com/geminilens-demo-mukunda/gemini-splunk-agent-demo.mp4 (2:18, 3.3 MB)
**License:** Apache 2.0

## What it does

You hand the agent a one-line symptom report ("checkout-api latency just
spiked"). It uses the Splunk MCP tools to gather evidence, reasons over
the metrics and logs with Gemini, and returns a structured root-cause
analysis: cited Problem ID, specific numbers, timestamps, and an
actionable next step for the on-call.

The agent uses the standard Splunk MCP tool surface (`list_problems`,
`execute_dql`, `find_entity_by_name`, `generate_dql_from_natural_language`,
etc.) — same as the official `splunk-oss/splunk-mcp` server. A local
**stub MCP server** ships with the repo so you can run end-to-end demos
without a Splunk tenant; flip one flag and the same agent code targets
a real tenant.

## Architecture

```
┌─────────────┐   user question      ┌─────────────────────────────┐
│  Streamlit  │ ───────────────────▶ │  ADK LlmAgent (Gemini 2.5)  │
│  dashboard  │                       │  on Vertex AI               │
└─────────────┘ ◀── final answer ──── └────┬────────────────────────┘
                                            │ MCPToolset / stdio
                                            ▼
                                   ┌─────────────────────────┐
                                   │  Splunk MCP server   │
                                   │  (stub by default,      │
                                   │  real tenant via flag)  │
                                   └─────────────────────────┘
```

## Try it locally (no Splunk tenant needed)

```bash
git clone https://github.com/MukundaKatta/gemini-splunk-agent
cd gemini-splunk-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# ADC for Vertex AI:
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=your-project
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_LOCATION=us-central1

# Streamlit dashboard:
PYTHONPATH=src streamlit run app/dashboard.py
```

Open the sidebar, type a production symptom, click Investigate.

## Try it against a real Splunk tenant

Set the official server credentials and flip the `stub` flag:

```bash
export DT_ENVIRONMENT_URL=https://abc12345.live.splunk.com
export DT_PLATFORM_TOKEN=dt0c01.XXXX...
```

In the dashboard sidebar, untick "Use stub Splunk MCP". The agent now
spawns the official `@splunk-oss/splunk-mcp-server` via npx and
talks to your real tenant.

## Programmatic use

```python
from gemini_splunk_agent.runner import ask

resp = ask("What's wrong with checkout-api?", stub=True, model="gemini-2.5-flash")
print(resp.final_text)
for event in resp.events:
    print(event)
```

## Self-observation

Every Gemini call inside the agent loop is wrapped with
[GeminiLens](https://github.com/MukundaKatta/geminilens) so the agent's
own cost, latency, and trace are recorded to
`~/.gemini-splunk-agent/traces.jsonl`. Useful for tracking how much each
investigation costs you in Vertex AI tokens.

## Repo layout

```
src/gemini_splunk_agent/
  agent.py        ADK LlmAgent definition + MCP toolset wiring
  runner.py       sync Python wrapper around ADK's async Runner
  mcp_stub.py     stub Splunk MCP server (stdio)
app/dashboard.py  Streamlit UI
tests/            pytest suite, 12 passing
Dockerfile        Cloud Run / Azure Container Apps image
```

## Tests

```bash
PYTHONPATH=src pytest -q
```

## License

Apache 2.0. Mukunda Katta, independent developer.

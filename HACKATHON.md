# Google Cloud Rapid Agent Hackathon — Splunk track submission

Devpost: https://rapid-agent.devpost.com
Deadline: 2026-06-11 14:00 PDT
Track: **Splunk**

This is a second submission from Mukunda Katta to the Google Cloud Rapid
Agent Hackathon, substantially different from ragvitals (RAG drift agent).
Per rule 7B, multiple submissions are allowed if they are "unique and
substantially different."

## How this submission satisfies each rule

| Rule | How we meet it |
|---|---|
| Powered by Gemini | gemini-2.5-flash via Vertex AI |
| Powered by Google Cloud Agent Builder | `google.adk.agents.LlmAgent` — Agent Development Kit |
| Integrates a Partner's MCP server | Tool surface matches `splunk-oss/splunk-mcp`; stub for demos, real tenant via env var |
| Newly created during Contest Period | Repo initialized 2026-05-17, well inside the May 5 – Jun 11 window |
| Original creation, not extension | Standalone repo. `geminilens` library is used as a pip dep, not the project itself |
| Open Source Initiative license at repo root | Apache 2.0, full license text |
| Runs on web | Streamlit dashboard, deployable to Cloud Run |

## Elevator pitch (under 200 chars on Devpost)
A Gemini agent built with Google's ADK that pulls Splunk problems and DQL
results via MCP, then reasons over them to give an SRE root-cause analysis.

## Description (paste into Devpost)
gemini-splunk-agent treats every production symptom as an SRE ticket. You ask
"why is the checkout-api latency spiking?" and the agent works the case:
calls `list_problems` on the Splunk MCP server to see what Splunk AI has
already detected, runs `execute_dql` to pull supporting metrics or logs,
resolves entity IDs with `find_entity_by_name` when needed, and translates
the user's question into a DQL query with
`generate_dql_from_natural_language` if necessary.

The output is the format an on-call engineer can act on: a one-line root
cause, 2-4 evidence bullets with specific timestamps and numbers, and a
concrete next step. The agent is built on Google Cloud's Agent Development
Kit (ADK) and runs Gemini 2.5 on Vertex AI. It talks to the Splunk MCP
server via the standard MCP protocol; a stub server ships in the repo so
reviewers can run end-to-end demos without a Splunk tenant, and the
same agent code targets a real tenant by setting two environment variables.

Every Gemini call inside the agent is also wrapped by GeminiLens, a small
observability library that records the agent's own cost, latency, and
tool-call audit log. The agent observes itself.

## Built with
python, gemini, gemini-2-5, vertex-ai, google-cloud-agent-builder,
agent-development-kit, mcp, splunk, splunk-mcp, streamlit,
google-cloud-run, geminilens, apache-2

## Try it out
- Code repo: https://github.com/MukundaKatta/gemini-splunk-agent
- Live demo (Cloud Run): https://gemini-splunk-agent-1029931682737.us-central1.run.app
- Demo video (local backup on GCS, 2:18, 3.3 MB): https://storage.googleapis.com/geminilens-demo-mukunda/gemini-splunk-agent-demo.mp4
- Demo video (YouTube unlisted): https://youtu.be/Vrar7099ks0

## Submission checklist
- [x] Powered by Gemini
- [x] Built with Google Cloud Agent Builder (ADK)
- [x] Integrates Splunk MCP server (tool surface compatible)
- [x] Newly created during Contest Period
- [x] OSI license at repo root (Apache 2.0)
- [x] Code repo public
- [ ] Hosted demo URL reachable
- [ ] 3-min demo video uploaded (YouTube or Vimeo per rules)
- [ ] Submission form filled on Devpost
- [ ] Splunk track selected

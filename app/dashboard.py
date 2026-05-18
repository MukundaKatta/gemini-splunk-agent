"""gemini-splunk-agent dashboard.

Run locally with:
    PYTHONPATH=src streamlit run app/dashboard.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gemini_splunk_agent.runner import ask  # noqa: E402


st.set_page_config(page_title="gemini-splunk-agent", layout="wide", page_icon=":mag:")
st.title("gemini-splunk-agent")
st.caption(
    "A Gemini agent for production incident investigation. Built on "
    "Google Cloud Agent Builder (ADK) and wired to the Splunk MCP server. "
    "Open source under Apache 2.0."
)

with st.sidebar:
    st.header("Run the agent")
    question = st.text_area(
        "What's the production problem?",
        value="My checkout-api latency just spiked. What changed?",
        height=110,
    )
    model = st.selectbox(
        "Gemini model",
        options=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"],
        index=0,
    )
    stub = st.toggle(
        "Use stub Splunk MCP",
        value=True,
        help="On = local stub server with canned realistic data. Off = real Splunk tenant (requires DT_ENVIRONMENT_URL + DT_PLATFORM_TOKEN).",
    )
    run = st.button("Investigate", type="primary", use_container_width=True)
    st.divider()
    st.caption(
        f"Project: `{os.getenv('GOOGLE_CLOUD_PROJECT', 'not-set')}`  "
        f"Vertex AI: `{os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'true')}`"
    )

st.markdown(
    """
This agent treats the user's symptom report as an SRE ticket and works
through the Splunk MCP tools to diagnose root cause:
- **list_alerts** for currently-firing Splunk alerts + Observability detectors
- **get_detector** for the detector rule + current value + baseline
- **run_search** for the SPL behind the alert (raw event records)
- **run_observability_query** to pull the underlying metric timeseries
- **list_indexes** when the user asks what data is on the cluster
"""
)

if run:
    with st.status("Running the agent against Vertex AI Gemini...", expanded=True) as status:
        t0 = time.perf_counter()
        try:
            resp = ask(question, stub=stub, model=model)
        except Exception as e:  # pragma: no cover
            status.update(label=f"Agent error: {e}", state="error")
            st.exception(e)
            st.stop()
        elapsed = (time.perf_counter() - t0) * 1000
        status.update(label=f"Done in {elapsed:.0f} ms", state="complete")

    st.subheader("Root cause analysis")
    st.markdown(resp.final_text or "_(no final response)_")

    with st.expander(f"Agent event trace ({len(resp.events)} events)"):
        for i, ev in enumerate(resp.events):
            st.markdown(
                f"**{i}.** author=`{ev.get('author')}` final=`{ev.get('is_final')}`"
            )
            text = ev.get("text") or ""
            if text:
                st.code(text[:1500], language=None)
else:
    st.info("Use the sidebar to fire an investigation against the stub Splunk MCP.")

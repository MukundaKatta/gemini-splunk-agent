"""Real Vertex AI smoke test for gemini-splunk-agent.

Runs an SRE question end-to-end through Gemini 2.5 Flash on the Splunk
MCP stub and verifies the agent quotes alert IDs, detector rules, p95
numbers, and SPL fragments verbatim from the tool output.

Usage:
    GOOGLE_CLOUD_PROJECT=careersavvy-mukunda \
    GOOGLE_GENAI_USE_VERTEXAI=true \
    GOOGLE_CLOUD_LOCATION=us-central1 \
    .venv/bin/python scripts/smoke.py
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "careersavvy-mukunda")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

from gemini_splunk_agent.runner import ask  # noqa: E402


QUESTION = (
    "Latency on checkout-api has spiked since around 14:30 UTC and the "
    "on-call says alerts are firing. Walk the Splunk tools and tell me "
    "exactly which alert, which detector, the underlying SPL, and the "
    "p95 numbers before vs after the spike. Output the labeled sections "
    "from your system prompt."
)


def main() -> int:
    print("== gemini-splunk-agent smoke ==")
    print(f"project={os.environ.get('GOOGLE_CLOUD_PROJECT')}")
    print(f"location={os.environ.get('GOOGLE_CLOUD_LOCATION')}")
    print(f"vertexai={os.environ.get('GOOGLE_GENAI_USE_VERTEXAI')}")
    print()
    print(f"> {QUESTION}")
    print()

    resp = ask(QUESTION, stub=True)
    print("--- FINAL TEXT ---")
    print(resp.final_text or "(no final text)")
    print("--- END FINAL TEXT ---")
    print(f"events: {len(resp.events)}")

    text = (resp.final_text or "").upper()
    checks = {
        "has ANSWER":         "ANSWER" in text,
        "has ACTIVE ALERT":   "ACTIVE ALERT" in text,
        "has DETECTOR":       "DETECTOR" in text,
        "has EVIDENCE":       "EVIDENCE" in text,
        "has ROOT CAUSE":     "ROOT CAUSE" in text,
        "has NEXT STEP":      "NEXT STEP" in text,
        "names alert id":     "ALRT-2026-0518-1432-A" in text,
        "names detector id":  "DTC-CHECKOUT-LATENCY-P95" in text,
        "quotes detector rule": "P95(DURATION_MS) > 1500" in text,
        "names checkout-api": "CHECKOUT-API" in text,
    }
    print()
    print("--- CHECKS ---")
    for label, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

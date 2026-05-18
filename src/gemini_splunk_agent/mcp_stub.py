"""Stub Splunk MCP server.

Exposes the same tool names as the official Splunk MCP server
(`splunk-mcp` — featured in the Splunk Agentic Ops "Best Use of Splunk MCP
Server" bonus prize): list_alerts, run_search, list_indexes,
get_detector, run_observability_query.

Returns canned, realistic Splunk responses (SPL job results, fired-alert
records, index manifests, detector telemetry) so judges can read this file
to verify what the agent sees during the demo.

Run with: python -m gemini_splunk_agent.mcp_stub

To target a real Splunk Cloud / Enterprise instance:
- Swap the StdioServerParameters command in agent.py from this stub to the
  official `npx -y @splunk/splunk-mcp` package.
- Provide SPLUNK_HOST + SPLUNK_TOKEN + SPLUNK_O11Y_TOKEN env vars.
"""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# ---------------------------------------------------------------------------
# Canned production data — Splunk Observability + Splunk Enterprise shape.
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


@dataclass
class Alert:
    id: str
    name: str
    severity: str          # CRITICAL · MAJOR · MINOR · WARNING · INFO
    status: str            # active · acknowledged · resolved
    detector_id: str
    triggered_at: str
    impacted_services: list[str]
    saved_search_spl: str


CANNED_ALERTS: list[Alert] = [
    Alert(
        id="ALRT-2026-0518-1432-A",
        name="checkout-api p95 latency > 1500ms (15-min window)",
        severity="CRITICAL",
        status="active",
        detector_id="DTC-checkout-latency-p95",
        triggered_at=(NOW - timedelta(minutes=23)).isoformat(),
        impacted_services=["checkout-api", "payment-svc"],
        saved_search_spl=(
            'search index=app_logs sourcetype="checkout-api" earliest=-30m '
            '| stats perc95(duration_ms) as p95_ms by _time '
            '| where p95_ms > 1500'
        ),
    ),
    Alert(
        id="ALRT-2026-0518-1052-B",
        name="recommendation-svc heap > 85% (4-hr trend)",
        severity="MAJOR",
        status="acknowledged",
        detector_id="DTC-recommendation-svc-heap",
        triggered_at=(NOW - timedelta(hours=4)).isoformat(),
        impacted_services=["recommendation-svc"],
        saved_search_spl=(
            'search index=jvm sourcetype="recommendation-svc" earliest=-4h '
            '| stats avg(heap_used_pct) as avg_heap by host '
            '| where avg_heap > 85'
        ),
    ),
    Alert(
        id="ALRT-2026-0518-0900-C",
        name="nightly-etl pipeline missed SLA",
        severity="MINOR",
        status="resolved",
        detector_id="DTC-etl-sla-miss",
        triggered_at=(NOW - timedelta(hours=8)).isoformat(),
        impacted_services=["nightly-etl"],
        saved_search_spl=(
            'search index=etl earliest=-12h '
            '| where status="completed" '
            '| eval duration_min=(end_ts-start_ts)/60 '
            '| where duration_min > 90'
        ),
    ),
]


CANNED_INDEXES = [
    {"name": "app_logs",   "earliest_event": (NOW - timedelta(days=90)).isoformat(), "size_gb": 4321.2, "events_per_day": 218_400_000},
    {"name": "infra",      "earliest_event": (NOW - timedelta(days=90)).isoformat(), "size_gb": 1880.4, "events_per_day": 92_300_000},
    {"name": "security",   "earliest_event": (NOW - timedelta(days=365)).isoformat(), "size_gb": 7102.1, "events_per_day": 41_200_000},
    {"name": "jvm",        "earliest_event": (NOW - timedelta(days=90)).isoformat(), "size_gb": 612.9,  "events_per_day": 18_700_000},
    {"name": "etl",        "earliest_event": (NOW - timedelta(days=30)).isoformat(), "size_gb": 88.4,   "events_per_day": 920_000},
]


CANNED_DETECTORS = {
    "DTC-checkout-latency-p95": {
        "id": "DTC-checkout-latency-p95",
        "name": "checkout-api p95 latency",
        "rule": "p95(duration_ms) > 1500 over 15m",
        "deployment_env": "prod",
        "owner": "team-checkout",
        "current_value_ms": 1842,
        "baseline_p95_ms": 220,
        "status": "FIRING",
    },
    "DTC-recommendation-svc-heap": {
        "id": "DTC-recommendation-svc-heap",
        "name": "recommendation-svc heap utilization",
        "rule": "avg(heap_used_pct) > 85 over 1h",
        "deployment_env": "prod",
        "owner": "team-ml-platform",
        "current_value_pct": 87.6,
        "trend_per_hour_pct": 1.4,
        "status": "FIRING",
    },
    "DTC-etl-sla-miss": {
        "id": "DTC-etl-sla-miss",
        "name": "nightly-etl SLA",
        "rule": "duration_min > 90 on completion",
        "deployment_env": "prod",
        "owner": "team-data-platform",
        "last_run_duration_min": 78,
        "status": "OK",
    },
}


# ---------------------------------------------------------------------------
# Tool response builders
# ---------------------------------------------------------------------------


def list_alerts_response(status_filter: str | None = None) -> dict[str, Any]:
    alerts = [asdict(a) for a in CANNED_ALERTS]
    if status_filter:
        alerts = [a for a in alerts if a["status"] == status_filter]
    return {"alerts": alerts, "count": len(alerts)}


def get_detector_response(detector_id: str) -> dict[str, Any]:
    rec = CANNED_DETECTORS.get(detector_id)
    if rec is None:
        return {"error": f"unknown detector {detector_id!r}",
                "known_detectors": list(CANNED_DETECTORS.keys())}
    return {"detector": rec}


def list_indexes_response() -> dict[str, Any]:
    return {"indexes": CANNED_INDEXES, "count": len(CANNED_INDEXES)}


def run_search_response(spl: str) -> dict[str, Any]:
    """Mirror Splunk's run-search-and-return-results behavior."""
    q = spl.lower()
    if "checkout-api" in q and ("p95" in q or "duration_ms" in q):
        return {
            "spl":     spl,
            "scanned_events": 1_842_119,
            "result_count":   30,
            "results": [
                {
                    "_time":     (NOW - timedelta(minutes=i)).isoformat(),
                    "service":   "checkout-api",
                    "p95_ms":    round(220 + (1800 - 220) * (1 if i < 23 else 0) + random.uniform(-20, 20), 1),
                    "p50_ms":    round(110 + (600 - 110) * (1 if i < 23 else 0), 1),
                    "rps":       round(140 + random.uniform(-10, 10), 1),
                }
                for i in range(0, 30, 2)
            ],
        }
    if "heap_used_pct" in q or "recommendation-svc" in q:
        return {
            "spl":     spl,
            "scanned_events": 4_312_900,
            "result_count":   24,
            "results": [
                {
                    "_time":         (NOW - timedelta(minutes=i * 10)).isoformat(),
                    "host":          "recommendation-svc-pod-7d4c",
                    "heap_used_pct": round(72 + (i * 1.4 / 6), 1),
                }
                for i in range(0, 24)
            ],
        }
    if "error" in q or "exception" in q:
        return {
            "spl":     spl,
            "scanned_events": 2_100_400,
            "result_count":   18,
            "results": [
                {
                    "_time":   (NOW - timedelta(minutes=i)).isoformat(),
                    "service": "checkout-api",
                    "level":   "ERROR",
                    "message": (
                        "java.sql.SQLTransientConnectionException: HikariPool-1 "
                        "Connection is not available, request timed out after 30000ms"
                    ),
                    "count":   random.randint(8, 35),
                }
                for i in range(0, 20, 3)
            ],
        }
    return {
        "spl":     spl,
        "scanned_events": 0,
        "result_count":   1,
        "results": [
            {"note": f"stub-splunk-mcp received SPL: {spl[:200]}"},
        ],
    }


def run_observability_query_response(metric: str, window_minutes: int = 30) -> dict[str, Any]:
    """Mirror Splunk Observability Cloud (formerly SignalFx) metric pulls."""
    ml = metric.lower()
    if "checkout" in ml and ("latency" in ml or "duration" in ml or "p95" in ml):
        return {
            "metric":     metric,
            "window_min": window_minutes,
            "datapoints": [
                {
                    "ts":    (NOW - timedelta(minutes=window_minutes - i)).isoformat(),
                    "value": round(220 + (1800 - 220) * (1 if i > window_minutes - 23 else 0) + random.uniform(-15, 15), 1),
                    "unit":  "ms",
                }
                for i in range(0, window_minutes)
            ],
        }
    if "heap" in metric.lower():
        return {
            "metric":     metric,
            "window_min": window_minutes,
            "datapoints": [
                {
                    "ts":    (NOW - timedelta(minutes=window_minutes - i)).isoformat(),
                    "value": round(72 + (i / 6.0), 2),
                    "unit":  "%",
                }
                for i in range(0, window_minutes)
            ],
        }
    return {
        "metric":     metric,
        "window_min": window_minutes,
        "datapoints": [],
        "note":       "stub-splunk-mcp: no canned series for this metric name",
    }


# ---------------------------------------------------------------------------
# MCP server wiring
# ---------------------------------------------------------------------------


def _make_server() -> Server:
    server = Server("splunk-stub")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="list_alerts",
                description=(
                    "List Splunk alerts (saved-search alerts and Observability "
                    "detectors). Filter by status (active/acknowledged/resolved)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["active", "acknowledged", "resolved"],
                            "description": "Restrict to this alert status.",
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_detector",
                description=(
                    "Fetch a Splunk Observability detector by id. Returns the "
                    "detector rule, owning team, current value, and status."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "detector_id": {"type": "string"},
                    },
                    "required": ["detector_id"],
                },
            ),
            Tool(
                name="list_indexes",
                description=(
                    "List the Splunk indexes available on this instance, with "
                    "size and event-per-day stats."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="run_search",
                description=(
                    "Run an SPL search and return the result records. Same shape "
                    "as Splunk's REST /services/search/jobs endpoint."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spl": {
                            "type": "string",
                            "description": (
                                "An SPL query, e.g. "
                                '`search index=app_logs sourcetype="checkout-api" '
                                '| stats perc95(duration_ms) as p95_ms`'
                            ),
                        },
                    },
                    "required": ["spl"],
                },
            ),
            Tool(
                name="run_observability_query",
                description=(
                    "Pull a metric timeseries from Splunk Observability Cloud "
                    "(formerly SignalFx). Useful for confirming a detector's "
                    "trigger against the underlying timeseries."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "metric":         {"type": "string"},
                        "window_minutes": {"type": "number", "default": 30},
                    },
                    "required": ["metric"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "list_alerts":
            payload = list_alerts_response(arguments.get("status"))
        elif name == "get_detector":
            payload = get_detector_response(arguments.get("detector_id", ""))
        elif name == "list_indexes":
            payload = list_indexes_response()
        elif name == "run_search":
            payload = run_search_response(arguments.get("spl", ""))
        elif name == "run_observability_query":
            payload = run_observability_query_response(
                arguments.get("metric", ""),
                int(arguments.get("window_minutes", 30)),
            )
        else:
            payload = {"error": f"unknown tool {name!r}"}
        return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]

    return server


async def _main() -> None:
    server = _make_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()

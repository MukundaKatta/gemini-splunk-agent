from gemini_splunk_agent.mcp_stub import (
    CANNED_ALERTS,
    CANNED_DETECTORS,
    CANNED_INDEXES,
    get_detector_response,
    list_alerts_response,
    list_indexes_response,
    run_observability_query_response,
    run_search_response,
)


def test_canned_alerts_loaded():
    assert len(CANNED_ALERTS) >= 3
    names = [a.name for a in CANNED_ALERTS]
    assert any("checkout-api" in n for n in names)


def test_list_alerts_returns_all_by_default():
    payload = list_alerts_response()
    assert payload["count"] == len(CANNED_ALERTS)
    assert any(a["id"] == "ALRT-2026-0518-1432-A" for a in payload["alerts"])


def test_list_alerts_status_filter():
    active = list_alerts_response("active")
    assert all(a["status"] == "active" for a in active["alerts"])
    assert active["count"] >= 1


def test_get_detector_known():
    payload = get_detector_response("DTC-checkout-latency-p95")
    assert payload["detector"]["status"] == "FIRING"
    assert payload["detector"]["current_value_ms"] == 1842


def test_get_detector_unknown_lists_known_ids():
    payload = get_detector_response("nope")
    assert "error" in payload
    assert "DTC-checkout-latency-p95" in payload["known_detectors"]


def test_list_indexes_returns_known_indexes():
    payload = list_indexes_response()
    names = [i["name"] for i in payload["indexes"]]
    assert "app_logs" in names
    assert "security" in names
    assert payload["count"] == len(CANNED_INDEXES)


def test_run_search_latency_query_shape():
    spl = ('search index=app_logs sourcetype="checkout-api" '
           '| stats perc95(duration_ms) as p95_ms by _time')
    payload = run_search_response(spl)
    assert payload["spl"] == spl
    assert payload["result_count"] == 30
    assert all(r["service"] == "checkout-api" for r in payload["results"])


def test_run_search_error_query_shape():
    payload = run_search_response('search index=app_logs level=ERROR')
    assert any(r.get("level") == "ERROR" for r in payload["results"])


def test_run_observability_latency_metric():
    payload = run_observability_query_response(
        "checkout-api.duration_ms.p95", window_minutes=30,
    )
    assert payload["window_min"] == 30
    assert len(payload["datapoints"]) == 30
    assert payload["datapoints"][0]["unit"] == "ms"


def test_run_observability_unknown_metric():
    payload = run_observability_query_response("unknown.metric.xyz")
    assert payload["datapoints"] == []


def test_detector_links_to_alert():
    """Every active alert must reference an existing detector."""
    for alert in CANNED_ALERTS:
        if alert.status == "active":
            assert alert.detector_id in CANNED_DETECTORS

#!/usr/bin/env python3
"""
Dashboard generator for K4-L3B Day 13 Monitoring & LLMOps.
Reads data/logs.jsonl and renders an interactive, self-contained HTML dashboard
with 6 panels and threshold lines adhering to config/dashboard.yaml.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

LOG_PATH = Path("data/logs.jsonl")
OUTPUT_PATH = Path("submission/evidence/dashboard.html")
YAML_CONFIG_PATH = Path("config/dashboard.yaml")


def parse_iso_ts(ts_str: str) -> datetime:
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def percentile(values: list[float | int], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    d = k - f
    return round(sorted_vals[f] + d * (sorted_vals[c] - sorted_vals[f]), 2)


def render_dashboard() -> Path:
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc - timedelta(minutes=60)

    records: list[dict[str, Any]] = []
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                rec_ts = parse_iso_ts(rec.get("ts", ""))
                rec["_dt"] = rec_ts
                records.append(rec)
            except Exception:
                continue

    # Filter records within last 60 minutes (or if empty, take all available)
    recent = [r for r in records if r["_dt"] >= start_time]
    if not recent and records:
        recent = records

    # 1. Latency Panel
    resp_sent = [r for r in recent if r.get("event") == "response_sent"]
    latencies = [r["latency_ms"] for r in resp_sent if isinstance(r.get("latency_ms"), (int, float))]
    ttfts = [r["ttft_ms"] for r in resp_sent if isinstance(r.get("ttft_ms"), (int, float))]

    p50_lat = percentile(latencies, 50)
    p95_lat = percentile(latencies, 95)
    p99_lat = percentile(latencies, 99)
    ttft_p95 = percentile(ttfts, 95)

    # 2. Traffic Panel
    req_recv = [r for r in recent if r.get("event") == "request_received"]
    traffic_count = len(req_recv)
    # bucket per minute
    minute_buckets: dict[str, int] = {}
    for r in req_recv:
        m_str = r["_dt"].strftime("%H:%M")
        minute_buckets[m_str] = minute_buckets.get(m_str, 0) + 1
    req_per_min = round(traffic_count / max(1, len(minute_buckets)), 2)

    # 3. Errors Panel
    req_failed = [r for r in recent if r.get("event") == "request_failed"]
    error_count = len(req_failed)
    total_reqs = max(traffic_count, len(resp_sent) + error_count)
    error_rate_pct = round((error_count / max(1, total_reqs)) * 100, 2)

    # retrieval success = count(tool_success == True) / count(tool_success != None) across ALL events
    tool_events = [r for r in recent if r.get("tool_success") is not None]
    tool_successes = [r for r in tool_events if r.get("tool_success") is True]
    tool_success_pct = round((len(tool_successes) / max(1, len(tool_events))) * 100, 2) if tool_events else 100.0

    error_types: dict[str, int] = {}
    for r in req_failed:
        etype = r.get("error_type", "UnknownError")
        error_types[etype] = error_types.get(etype, 0) + 1

    # 4. Cost Panel
    costs = [r["cost_usd"] for r in resp_sent if isinstance(r.get("cost_usd"), (int, float))]
    total_cost = round(sum(costs), 6)
    cost_buckets: dict[str, float] = {}
    for r in resp_sent:
        m_str = r["_dt"].strftime("%H:%M")
        cost_buckets[m_str] = round(cost_buckets.get(m_str, 0.0) + float(r.get("cost_usd", 0.0)), 6)

    # 5. Tokens Panel
    tokens_in = sum(int(r.get("tokens_in", 0)) for r in resp_sent if isinstance(r.get("tokens_in"), (int, float)))
    tokens_out = sum(int(r.get("tokens_out", 0)) for r in resp_sent if isinstance(r.get("tokens_out"), (int, float)))
    total_tokens = tokens_in + tokens_out

    # 6. Quality Panel
    quality_scores = [r["quality_score"] for r in resp_sent if isinstance(r.get("quality_score"), (int, float))]
    mean_quality = round(sum(quality_scores) / max(1, len(quality_scores)), 2) if quality_scores else 0.0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <title>K4-L3B Day 13 Monitoring & LLMOps Dashboard</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --border-color: #30363d;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --accent-yellow: #d29922;
            --accent-purple: #bc8cff;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background-color: var(--bg-color); color: var(--text-main); padding: 24px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid var(--border-color); padding-bottom: 16px; }}
        .header h1 {{ font-size: 22px; font-weight: 600; color: #fff; }}
        .header .meta {{ font-size: 13px; color: var(--text-muted); display: flex; gap: 16px; }}
        .badge {{ background: #21262d; border: 1px solid var(--border-color); padding: 4px 8px; border-radius: 6px; font-family: monospace; font-size: 12px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; display: flex; flex-direction: column; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }}
        .card-title {{ font-size: 15px; font-weight: 600; color: #f0f6fc; }}
        .card-unit {{ font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
        .threshold-pill {{ font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(248, 81, 73, 0.15); color: var(--accent-red); border: 1px solid rgba(248, 81, 73, 0.4); margin-bottom: 12px; display: inline-block; width: fit-content; }}
        .metrics-summary {{ display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }}
        .metric-item {{ flex: 1; min-width: 70px; background: #0d1117; padding: 10px; border-radius: 6px; border: 1px solid #21262d; }}
        .metric-label {{ font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }}
        .metric-value {{ font-size: 18px; font-weight: 700; color: #fff; }}
        .chart-box {{ width: 100%; height: 130px; margin-top: auto; display: flex; align-items: flex-end; gap: 4px; border-bottom: 1px solid var(--border-color); position: relative; padding-top: 20px; }}
        .threshold-line {{ position: absolute; left: 0; right: 0; border-top: 2px dashed var(--accent-red); pointer-events: none; z-index: 10; }}
        .threshold-label {{ position: absolute; right: 4px; top: -14px; font-size: 10px; color: var(--accent-red); font-weight: bold; background: rgba(13, 17, 23, 0.8); padding: 0 4px; }}
        .bar-group {{ flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; height: 100%; }}
        .bar {{ width: 80%; background: var(--accent-blue); border-radius: 3px 3px 0 0; min-height: 2px; transition: height 0.3s; }}
        .bar.green {{ background: var(--accent-green); }}
        .bar.yellow {{ background: var(--accent-yellow); }}
        .bar.purple {{ background: var(--accent-purple); }}
        .bar-label {{ font-size: 9px; color: var(--text-muted); margin-top: 4px; }}
        .status-ok {{ color: var(--accent-green); }}
        .status-warn {{ color: var(--accent-yellow); }}
        .status-bad {{ color: var(--accent-red); }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>K4-L3B Day 13 Monitoring &amp; LLMOps Dashboard</h1>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Contract: config/dashboard.yaml &bull; Source: data/logs.jsonl</div>
        </div>
        <div class="meta">
            <span class="badge">Time Range: Last 60m (UTC)</span>
            <span class="badge">Refresh: 30s</span>
            <span class="badge">Records: {len(records)} ({len(recent)} in window)</span>
        </div>
    </div>

    <div class="grid">
        <!-- 1. Latency Panel -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">1. Latency percentiles and TTFT</span>
                <span class="card-unit">ms</span>
            </div>
            <span class="threshold-pill">Threshold: P95 &le; 3000 ms</span>
            <div class="metrics-summary">
                <div class="metric-item">
                    <div class="metric-label">P50</div>
                    <div class="metric-value">{p50_lat} ms</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">P95</div>
                    <div class="metric-value {'status-ok' if p95_lat <= 3000 else 'status-bad'}">{p95_lat} ms</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">P99</div>
                    <div class="metric-value">{p99_lat} ms</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">TTFT P95</div>
                    <div class="metric-value">{ttft_p95} ms</div>
                </div>
            </div>
            <div class="chart-box">
                <div class="threshold-line" style="bottom: 75%;">
                    <span class="threshold-label">SLO Threshold: 3000ms</span>
                </div>
                <div class="bar-group"><div class="bar" style="height: {min(100, max(5, int(p50_lat / 40)))}%;"></div><span class="bar-label">P50</span></div>
                <div class="bar-group"><div class="bar" style="height: {min(100, max(5, int(p95_lat / 40)))}%;"></div><span class="bar-label">P95</span></div>
                <div class="bar-group"><div class="bar" style="height: {min(100, max(5, int(p99_lat / 40)))}%;"></div><span class="bar-label">P99</span></div>
                <div class="bar-group"><div class="bar purple" style="height: {min(100, max(5, int(ttft_p95 / 40)))}%;"></div><span class="bar-label">TTFT</span></div>
            </div>
        </div>

        <!-- 2. Traffic Panel -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">2. Request traffic</span>
                <span class="card-unit">requests_per_minute</span>
            </div>
            <span class="threshold-pill">Threshold: Rate &ge; 1 req/min</span>
            <div class="metrics-summary">
                <div class="metric-item">
                    <div class="metric-label">Total Requests</div>
                    <div class="metric-value">{traffic_count}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Active Minutes</div>
                    <div class="metric-value">{max(1, len(minute_buckets))} min</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Req / min Rate</div>
                    <div class="metric-value {'status-ok' if req_per_min >= 1 else 'status-warn'}">{req_per_min}</div>
                </div>
            </div>
            <div class="chart-box">
                <div class="threshold-line" style="bottom: 25%;">
                    <span class="threshold-label">Threshold: 1 req/min</span>
                </div>
                {"".join(f'<div class="bar-group"><div class="bar green" style="height: {min(100, max(10, count * 15))}%;"></div><span class="bar-label">{minute}</span></div>' for minute, count in list(minute_buckets.items())[-8:]) if minute_buckets else '<div style="color:var(--text-muted);font-size:12px;margin:auto;">No traffic yet</div>'}
            </div>
        </div>

        <!-- 3. Errors Panel -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">3. Error rate and retrieval success</span>
                <span class="card-unit">percent (%)</span>
            </div>
            <span class="threshold-pill">Threshold: Error &le; 2% | Retrieval &ge; 90%</span>
            <div class="metrics-summary">
                <div class="metric-item">
                    <div class="metric-label">Error Rate</div>
                    <div class="metric-value {'status-ok' if error_rate_pct <= 2 else 'status-bad'}">{error_rate_pct}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Retrieval Success</div>
                    <div class="metric-value {'status-ok' if tool_success_pct >= 90 else 'status-bad'}">{tool_success_pct}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Failed Requests</div>
                    <div class="metric-value">{error_count}</div>
                </div>
            </div>
            <div class="chart-box">
                <div class="threshold-line" style="bottom: 20%;">
                    <span class="threshold-label">Error Max: 2%</span>
                </div>
                <div class="bar-group"><div class="bar green" style="height: {max(5, int(tool_success_pct))}%;"></div><span class="bar-label">Retrieval</span></div>
                <div class="bar-group"><div class="bar {'yellow' if error_rate_pct <= 2 else 'status-bad'}" style="height: {max(5, min(100, int(error_rate_pct * 5)))}%;"></div><span class="bar-label">Error %</span></div>
                {"".join(f'<div class="bar-group"><div class="bar" style="background:#f85149;height:{min(100, max(10, c * 20))}%;"></div><span class="bar-label">{et[:6]}</span></div>' for et, c in list(error_types.items())[:3])}
            </div>
        </div>

        <!-- 4. Cost Panel -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">4. Cost over time</span>
                <span class="card-unit">USD ($)</span>
            </div>
            <span class="threshold-pill">Threshold: Total &le; $2.50</span>
            <div class="metrics-summary">
                <div class="metric-item">
                    <div class="metric-label">Total Window Cost</div>
                    <div class="metric-value {'status-ok' if total_cost <= 2.5 else 'status-bad'}">${total_cost:.5f}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Avg Cost / Req</div>
                    <div class="metric-value">${(total_cost / max(1, len(resp_sent))):.5f}</div>
                </div>
            </div>
            <div class="chart-box">
                <div class="threshold-line" style="bottom: 85%;">
                    <span class="threshold-label">Daily Threshold: $2.50</span>
                </div>
                {"".join(f'<div class="bar-group"><div class="bar yellow" style="height: {min(100, max(10, int(c * 2000)))}%;"></div><span class="bar-label">{minute}</span></div>' for minute, c in list(cost_buckets.items())[-8:]) if cost_buckets else '<div style="color:var(--text-muted);font-size:12px;margin:auto;">No cost data</div>'}
            </div>
        </div>

        <!-- 5. Tokens Panel -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">5. Input and output tokens</span>
                <span class="card-unit">tokens</span>
            </div>
            <span class="threshold-pill">Threshold: Sum &le; 50,000 tokens</span>
            <div class="metrics-summary">
                <div class="metric-item">
                    <div class="metric-label">Tokens In</div>
                    <div class="metric-value">{tokens_in:,}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Tokens Out</div>
                    <div class="metric-value">{tokens_out:,}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Total Tokens</div>
                    <div class="metric-value {'status-ok' if total_tokens <= 50000 else 'status-bad'}">{total_tokens:,}</div>
                </div>
            </div>
            <div class="chart-box">
                <div class="threshold-line" style="bottom: 80%;">
                    <span class="threshold-label">Threshold: 50,000</span>
                </div>
                <div class="bar-group"><div class="bar" style="height: {min(100, max(5, int((tokens_in / max(1, total_tokens)) * 80)))}%;"></div><span class="bar-label">Input</span></div>
                <div class="bar-group"><div class="bar purple" style="height: {min(100, max(5, int((tokens_out / max(1, total_tokens)) * 80)))}%;"></div><span class="bar-label">Output</span></div>
                <div class="bar-group"><div class="bar green" style="height: {min(100, max(10, int((total_tokens / 50000) * 80)))}%;"></div><span class="bar-label">Total</span></div>
            </div>
        </div>

        <!-- 6. Quality Panel -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">6. Quality proxy</span>
                <span class="card-unit">score (0 to 1)</span>
            </div>
            <span class="threshold-pill">Threshold: Mean &ge; 0.75</span>
            <div class="metrics-summary">
                <div class="metric-item">
                    <div class="metric-label">Mean Quality</div>
                    <div class="metric-value {'status-ok' if mean_quality >= 0.75 else 'status-bad'}">{mean_quality} / 1.0</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Evaluated Reqs</div>
                    <div class="metric-value">{len(quality_scores)}</div>
                </div>
            </div>
            <div class="chart-box">
                <div class="threshold-line" style="bottom: 75%;">
                    <span class="threshold-label">Threshold: &ge; 0.75</span>
                </div>
                {"".join(f'<div class="bar-group"><div class="bar {"green" if q >= 0.75 else "yellow"}" style="height: {int(q * 90)}%;"></div><span class="bar-label">#{i+1}</span></div>' for i, q in enumerate(quality_scores[-8:])) if quality_scores else '<div style="color:var(--text-muted);font-size:12px;margin:auto;">No quality data</div>'}
            </div>
        </div>
    </div>
</body>
</html>
"""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard generated successfully at: {OUTPUT_PATH.resolve()}")
    return OUTPUT_PATH


if __name__ == "__main__":
    render_dashboard()

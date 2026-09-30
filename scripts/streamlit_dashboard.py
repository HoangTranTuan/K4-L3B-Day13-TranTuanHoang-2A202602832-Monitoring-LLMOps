"""
Streamlit dashboard for K4-L3B Day 13 Monitoring & LLMOps.
Run in a separate virtual environment:
    streamlit run scripts/streamlit_dashboard.py
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
except ImportError:
    st = None

LOG_PATH = Path("data/logs.jsonl")


def main():
    if st is None:
        print("Streamlit or plotly not installed in this environment. Run in an isolated venv.")
        return

    st.set_page_config(page_title="Day 13 LLMOps Dashboard", layout="wide")
    st.title("K4-L3B Day 13 Monitoring & LLMOps Dashboard")
    st.caption("Contract: config/dashboard.yaml | Data source: data/logs.jsonl | Time range: 60m")

    if not LOG_PATH.exists():
        st.warning("data/logs.jsonl not found. Run load_test.py first.")
        return

    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    if not records:
        st.info("No logs found.")
        return

    df = pd.DataFrame(records)
    if "ts" in df.columns:
        df["dt"] = pd.to_datetime(df["ts"], utc=True)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
        df_60m = df[df["dt"] >= cutoff]
        if df_60m.empty:
            df_60m = df
    else:
        df_60m = df

    col1, col2 = st.columns(2)

    # Panel 1: Latency
    with col1:
        st.subheader("1. Latency percentiles and TTFT (ms)")
        resp = df_60m[df_60m["event"] == "response_sent"]
        if not resp.empty and "latency_ms" in resp.columns:
            p50 = resp["latency_ms"].quantile(0.5)
            p95 = resp["latency_ms"].quantile(0.95)
            p99 = resp["latency_ms"].quantile(0.99)
            ttft = resp["ttft_ms"].quantile(0.95) if "ttft_ms" in resp.columns else 0
            fig = go.Figure()
            fig.add_trace(go.Bar(x=["P50", "P95", "P99", "TTFT P95"], y=[p50, p95, p99, ttft], name="Latency"))
            fig.add_hline(y=3000, line_dash="dash", line_color="red", annotation_text="Threshold P95 <= 3000ms")
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
            st.metric("P95 Latency", f"{p95:.1f} ms", delta=f"{3000 - p95:.1f} ms margin")

    # Panel 2: Traffic
    with col2:
        st.subheader("2. Request traffic (requests_per_minute)")
        reqs = df_60m[df_60m["event"] == "request_received"]
        if not reqs.empty and "dt" in reqs.columns:
            ts_counts = reqs.set_index("dt").resample("1min").count()["event"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_counts.index, y=ts_counts.values, mode="lines+markers", name="Traffic"))
            fig.add_hline(y=1, line_dash="dash", line_color="red", annotation_text="Threshold >= 1 req/min")
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Total Requests", len(reqs))

    col3, col4 = st.columns(2)

    # Panel 3: Errors
    with col3:
        st.subheader("3. Error rate and retrieval success (%)")
        total_req = len(df_60m[df_60m["event"] == "request_received"])
        failed_req = len(df_60m[df_60m["event"] == "request_failed"])
        error_rate = (failed_req / max(1, total_req)) * 100

        tool_events = df_60m[df_60m["tool_success"].notna()]
        retrieval_success = (len(tool_events[tool_events["tool_success"] == True]) / max(1, len(tool_events))) * 100

        fig = go.Figure()
        fig.add_trace(go.Bar(x=["Error Rate %", "Retrieval Success %"], y=[error_rate, retrieval_success]))
        fig.add_hline(y=2, line_dash="dash", line_color="red", annotation_text="Max Error: 2%")
        fig.add_hline(y=90, line_dash="dash", line_color="green", annotation_text="Min Retrieval: 90%")
        fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # Panel 4: Cost
    with col4:
        st.subheader("4. Cost over time (USD)")
        if not resp.empty and "cost_usd" in resp.columns:
            total_cost = resp["cost_usd"].sum()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=["Total Cost ($)"], y=[total_cost]))
            fig.add_hline(y=2.5, line_dash="dash", line_color="red", annotation_text="Threshold <= $2.50")
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Total Cost", f"${total_cost:.5f}", delta=f"${2.5 - total_cost:.4f} remaining")

    col5, col6 = st.columns(2)

    # Panel 5: Tokens
    with col5:
        st.subheader("5. Input and output tokens (tokens)")
        if not resp.empty and "tokens_in" in resp.columns:
            tok_in = resp["tokens_in"].sum()
            tok_out = resp["tokens_out"].sum()
            total_tok = tok_in + tok_out
            fig = go.Figure()
            fig.add_trace(go.Bar(x=["Tokens In", "Tokens Out", "Total Tokens"], y=[tok_in, tok_out, total_tok]))
            fig.add_hline(y=50000, line_dash="dash", line_color="red", annotation_text="Threshold <= 50,000")
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Total Tokens", f"{total_tok:,}")

    # Panel 6: Quality
    with col6:
        st.subheader("6. Quality proxy (0 to 1)")
        if not resp.empty and "quality_score" in resp.columns:
            mean_qual = resp["quality_score"].mean()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=["Average Quality Score"], y=[mean_qual]))
            fig.add_hline(y=0.75, line_dash="dash", line_color="red", annotation_text="Threshold >= 0.75")
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Mean Quality", f"{mean_qual:.2f} / 1.0")


if __name__ == "__main__":
    main()

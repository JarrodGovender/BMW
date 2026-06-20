"""Super User SOC dashboard: live server metrics + active-session heartbeat."""
import pandas as pd
import streamlit as st

from utils import telemetry

try:
    import psutil
except ImportError:
    psutil = None


def render(supabase, container_bg="#1c1c1c", text_color="#ffffff"):
    st.subheader("🛰️ System Health & Telemetry")
    st.caption("Live server resource usage and Streamlit render performance for this process.")

    _render_server_metrics()
    st.divider()
    _render_app_performance()
    st.divider()
    _render_active_users(supabase)


def _render_server_metrics():
    st.markdown("##### 🖥️ Server Resources")
    if psutil is None:
        st.warning("`psutil` is not installed in this environment — server resource metrics are unavailable. Add `psutil` to requirements.txt and reinstall.")
        return

    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CPU Usage", f"{cpu_pct:.1f}%")
    c2.metric("RAM Usage", f"{mem.percent:.1f}%", f"{mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB")
    c3.metric("Disk Usage", f"{disk.percent:.1f}%", f"{disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB")

    try:
        proc = psutil.Process()
        proc_mem_mb = proc.memory_info().rss / (1024**2)
        c4.metric("App Process RAM", f"{proc_mem_mb:.0f} MB")
    except Exception:
        c4.metric("App Process RAM", "N/A")


def _render_app_performance():
    st.markdown("##### ⚡ App Performance")
    metrics = telemetry.get_process_metrics()

    uptime_min = metrics["uptime_seconds"] / 60
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reruns Served", f"{metrics['render_count']:,}")
    c2.metric("Avg Render Time", f"{metrics['render_time_avg'] * 1000:.0f} ms")
    c3.metric("Last Render Time", f"{metrics['render_time_last'] * 1000:.0f} ms")
    c4.metric("Process Uptime", f"{uptime_min:.1f} min")

    if metrics["render_time_max"] > 1.0:
        st.warning(f"Slowest render this session was {metrics['render_time_max']:.2f}s — investigate if this becomes frequent.")


def _render_active_users(supabase):
    st.markdown(f"##### 🟢 Active Users (last {telemetry.ACTIVE_WINDOW_MINUTES} min)")
    active = telemetry.get_active_users(supabase)

    if not active:
        st.info("No active heartbeats found. Either no one else is online, or the `users` table is missing the `last_active_timestamp` column — see the SQL setup note below.")
    else:
        df = pd.DataFrame(active)
        cols = [c for c in ["username", "name", "role", "location_id", "minutes_ago"] if c in df.columns]
        df = df[cols].rename(columns={
            "username": "Username", "name": "Name", "role": "Role",
            "location_id": "Location", "minutes_ago": "Mins Ago",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("ℹ️ Schema requirement"):
        st.code(
            "alter table users add column if not exists last_active_timestamp timestamptz;",
            language="sql",
        )
        st.caption("Run this once in Supabase SQL editor. Until it's applied, the heartbeat write is silently skipped and this table stays empty.")

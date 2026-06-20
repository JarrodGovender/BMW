"""
Process-wide telemetry for the Super User SOC dashboard.

st.session_state is per-browser-session and can't hold cross-user data, so
render timings/request counts live in a singleton dict via st.cache_resource
(one instance shared by every session in the same server process). The
active-users heartbeat is different: it has to be visible across server
processes/restarts too, so it's persisted to the `users` table in Supabase
instead of kept in memory.
"""
import time
from datetime import datetime, timezone

import streamlit as st

from utils.rate_limiter import throttled

HEARTBEAT_COOLDOWN_SECONDS = 30
ACTIVE_WINDOW_MINUTES = 5


@st.cache_resource
def _process_metrics_store():
    return {
        "render_count": 0,
        "render_time_total": 0.0,
        "render_time_last": 0.0,
        "render_time_max": 0.0,
        "started_at": time.time(),
    }


def record_render_time(seconds):
    """Call once per script rerun with the elapsed render duration."""
    store = _process_metrics_store()
    store["render_count"] += 1
    store["render_time_total"] += seconds
    store["render_time_last"] = seconds
    store["render_time_max"] = max(store["render_time_max"], seconds)


def get_process_metrics():
    store = _process_metrics_store()
    count = store["render_count"] or 1
    return {
        "render_count": store["render_count"],
        "render_time_avg": store["render_time_total"] / count,
        "render_time_last": store["render_time_last"],
        "render_time_max": store["render_time_max"],
        "uptime_seconds": time.time() - store["started_at"],
    }


def heartbeat(supabase):
    """Stamp last_active_timestamp for the logged-in user, throttled so it
    doesn't fire a write on every single rerun. Silently no-ops if the
    column doesn't exist yet on the live schema."""
    username = st.session_state.get("user")
    if not username:
        return
    if throttled("_telemetry_heartbeat", cooldown=HEARTBEAT_COOLDOWN_SECONDS):
        return
    try:
        supabase.table("users").update(
            {"last_active_timestamp": datetime.now(timezone.utc).isoformat()}
        ).eq("username", username).execute()
    except Exception:
        pass


def get_active_users(supabase):
    """Users whose last_active_timestamp falls within ACTIVE_WINDOW_MINUTES.
    Returns [] (rather than raising) if the column isn't on the schema yet."""
    try:
        resp = supabase.table("users").select(
            "username, name, role, role_id, location_id, last_active_timestamp"
        ).execute()
    except Exception:
        return []
    rows = resp.data or []
    active = []
    now = datetime.now(timezone.utc)
    for row in rows:
        ts = row.get("last_active_timestamp")
        if not ts:
            continue
        try:
            stamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        age_minutes = (now - stamp).total_seconds() / 60
        if age_minutes <= ACTIVE_WINDOW_MINUTES:
            row["minutes_ago"] = round(age_minutes, 1)
            active.append(row)
    active.sort(key=lambda r: r["minutes_ago"])
    return active

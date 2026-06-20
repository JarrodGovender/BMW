"""
Admin / God Mode console -- reachable only by SUPER_USER_ROLES (see
utils/helpers.is_super_user). Bundles the system-level tools that don't
belong on any single departmental page: appearance/data-source settings,
a recent-activity log, a raw-table viewer, and user/token management.
"""
import streamlit as st
from views import settings as settings_view
from views.shared_utils import _render_token_manager

RAW_DATA_TABLES = [
    "used_car_stock", "service_wip", "deal_desk", "parts_otc",
    "doc_expenses", "sales_pipeline", "crm_leads", "leads",
    "individual_leads", "tender_leads", "users", "auth_tokens",
]

# Tables with a created_at column we can use to build a unified recent-
# activity feed -- the closest thing to a system log without a dedicated
# audit table in the schema.
LOG_SOURCES = ["deal_desk", "service_wip", "parts_otc", "doc_expenses"]


def render(supabase):
    st.markdown("## 👑 ADMIN / GOD MODE")
    st.caption("Enterprise-wide tools -- visible only to Super User roles.")

    t1, t2, t3, t4 = st.tabs(["⚙️ SETTINGS", "🪵 LOGS", "🗄️ RAW DATA", "👥 USER MANAGEMENT"])

    with t1:
        settings_view.render(supabase)

    with t2:
        _render_logs(supabase)

    with t3:
        _render_raw_data(supabase)

    with t4:
        _render_token_manager(supabase)


def _render_logs(supabase):
    st.markdown("#### RECENT SYSTEM ACTIVITY")
    st.caption("Most recent rows across deal_desk / service_wip / parts_otc / doc_expenses, unfiltered.")

    rows = []
    for table in LOG_SOURCES:
        try:
            res = supabase.table(table).select("*").order("created_at", desc=True).limit(25).execute().data
        except Exception:
            res = []
        for r in res:
            rows.append({
                "TABLE": table,
                "CREATED": r.get("created_at", ""),
                "LOCATION": r.get("location_id", ""),
                "DETAIL": r.get("client_name") or r.get("description") or r.get("notes") or "",
            })

    if not rows:
        st.info("No recent activity found (or running on demo/empty data).")
        return

    rows.sort(key=lambda r: r["CREATED"], reverse=True)
    st.dataframe(rows[:100], use_container_width=True, hide_index=True)


def _render_raw_data(supabase):
    st.markdown("#### RAW TABLE VIEWER")
    st.caption("Unfiltered Supabase table contents -- bypasses the location/department/brand matrix.")

    table = st.selectbox("Table:", RAW_DATA_TABLES, key="admin_raw_table_select")
    limit = st.slider("Row limit:", 10, 1000, 200, step=10, key="admin_raw_table_limit")

    if st.button("🔍 LOAD", key="admin_raw_table_load"):
        try:
            res = supabase.table(table).select("*").limit(limit).execute().data
            if res:
                st.dataframe(res, use_container_width=True, hide_index=True)
                st.caption(f"{len(res)} row(s).")
            else:
                st.info("Table is empty.")
        except Exception as e:
            st.error(f"Error loading `{table}`: {e}")

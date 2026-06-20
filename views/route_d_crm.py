import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config import safe_rerun, SAST
from utils.helpers import get_role

# ====================================================================
# ROUTE D: CRM PIPELINE (PHASE VI CADENCE ENGINE)
#
# Security matrix is bespoke here rather than apply_matrix_filters() from
# shared_utils.py: SALES_REP (this codebase's individual-contributor sales
# role -- "SALES_EXEC" doesn't exist in the role vocabulary anywhere else
# in this app, see scripts/seed_crm_leads.py) must see only leads assigned
# to them, which none of apply_matrix_filters()'s existing buckets do.
# Management/Director still get the usual location-scoped / full-bypass
# treatment.
# ====================================================================
def render_crm(supabase, user_data=None):
    role = get_role()
    username = st.session_state.get('user')
    location = st.session_state.get('location_id')

    st.markdown("## 🎯 CRM PIPELINE — CADENCE ENGINE")

    try:
        query = supabase.table("crm_leads").select("*")
        if role == 'SALES_REP':
            query = query.eq("assigned_exec", username)
        elif role != 'DIRECTOR':
            query = query.eq("location_id", location)
        leads = query.order("next_action_due").execute().data or []
    except Exception as e:
        st.error(f"❌ Failed to load CRM pipeline: {e}")
        leads = []

    df = pd.DataFrame(leads)
    now = datetime.now(SAST)

    if not df.empty:
        df['next_action_due_dt'] = pd.to_datetime(df['next_action_due'], errors='coerce', utc=True)
        df['estimated_value'] = pd.to_numeric(df.get('estimated_value', 0), errors='coerce').fillna(0.0)
        active_df = df[df['status'] != 'Closed']
        total_active = len(active_df)
        hot_leads = len(active_df[active_df['temperature'] == 'Hot'])
        now_utc = pd.Timestamp.now(tz='UTC')
        breaches_24h = len(active_df[active_df['next_action_due_dt'] < now_utc])
        pipeline_value = active_df['estimated_value'].sum()
    else:
        total_active = hot_leads = breaches_24h = 0
        pipeline_value = 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL ACTIVE LEADS", f"{total_active}")
    m2.metric("🔥 HOT LEADS", f"{hot_leads}")
    m3.metric("⚠️ 24HR BREACHES", f"{breaches_24h}")
    m4.metric("PIPELINE VALUE", f"R {pipeline_value:,.0f}")

    st.markdown("---")

    # ----------------------------------------------------------------
    # INTAKE FORM
    # ----------------------------------------------------------------
    with st.expander("➕ INITIATE NEW LEAD"):
        try:
            exec_pool = (
                supabase.table("users")
                .select("username, name")
                .eq("location_id", location)
                .eq("is_active", True)
                .execute()
                .data
                or []
            )
        except Exception:
            exec_pool = []
        exec_options = ["Unassigned"] + [u['username'] for u in exec_pool]
        default_exec_idx = exec_options.index(username) if username in exec_options else 0

        with st.form("crm_intake_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            customer_name = c1.text_input("CUSTOMER NAME")
            contact_number = c2.text_input("CONTACT NUMBER")
            vehicle_of_interest = c1.text_input("VEHICLE OF INTEREST")
            source = c2.selectbox("SOURCE", ["Website Enquiry", "Walk-in", "AutoTrader", "Referral", "Showroom Floor", "Call-in Campaign"])

            c3, c4, c5 = st.columns(3)
            status = c3.selectbox("STATUS", ["New", "Contacted", "Test Drive", "Negotiation", "Closed"])
            temperature = c4.selectbox("TEMPERATURE", ["Cold", "Warm", "Hot"], index=1)
            estimated_value = c5.number_input("ESTIMATED VALUE (ZAR)", min_value=0.0, step=5000.0)

            c6, c7 = st.columns(2)
            next_action_due = c6.date_input("NEXT ACTION DUE", value=(now + timedelta(days=1)).date())
            assigned_exec_sel = c7.selectbox("ASSIGN TO", exec_options, index=default_exec_idx)

            if st.form_submit_button("🚀 CREATE LEAD", use_container_width=True):
                if not customer_name:
                    st.error("❌ Customer name is required.")
                else:
                    payload = {
                        "customer_name": customer_name,
                        "contact_number": contact_number,
                        "vehicle_of_interest": vehicle_of_interest,
                        "source": source,
                        "status": status,
                        "temperature": temperature,
                        "last_contact": now.isoformat(),
                        "next_action_due": datetime.combine(next_action_due, datetime.min.time()).isoformat(),
                        "estimated_value": estimated_value,
                        "assigned_exec": None if assigned_exec_sel == "Unassigned" else assigned_exec_sel,
                        "location_id": location,
                        "department_id": st.session_state.get('department_id', 'NEW_SALES'),
                        "brand_id": st.session_state.get('brand_id', 'ALL_BRANDS'),
                    }
                    try:
                        supabase.table("crm_leads").insert(payload).execute()
                        st.success(f"✅ Lead for {customer_name} created.")
                        safe_rerun()
                    except Exception as e:
                        st.error(f"❌ Database rejection: {e}")

    st.markdown("---")

    # ----------------------------------------------------------------
    # ACTIVE ORDER BOOK
    # ----------------------------------------------------------------
    st.markdown("### 📖 ACTIVE ORDER BOOK")
    if df.empty:
        st.info("No leads in scope for your current matrix view.")
    else:
        display_df = df.rename(columns={
            "customer_name": "CUSTOMER", "contact_number": "CONTACT", "vehicle_of_interest": "VEHICLE",
            "source": "SOURCE", "status": "STATUS", "temperature": "TEMP", "assigned_exec": "EXEC",
            "estimated_value": "EST. VALUE", "next_action_due": "NEXT ACTION DUE", "location_id": "BRANCH",
        })
        cols = ["CUSTOMER", "VEHICLE", "STATUS", "TEMP", "EST. VALUE", "EXEC", "BRANCH", "NEXT ACTION DUE", "CONTACT", "SOURCE"]
        cols = [c for c in cols if c in display_df.columns]
        st.dataframe(display_df[cols], hide_index=True, use_container_width=True)

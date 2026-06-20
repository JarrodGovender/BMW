"""Super User access & session-termination center: password overrides,
force-logout, and account revocation."""
import hashlib

import pandas as pd
import streamlit as st

from config import safe_rerun
from utils.rate_limiter import throttled


def render(supabase):
    st.subheader("🔐 User Access & Session Control")
    st.caption("Override credentials, force a re-login, or revoke access entirely for any account.")

    try:
        users = supabase.table("users").select("*").order("username").execute().data
    except Exception as e:
        st.error(f"❌ Could not load users: {e}")
        return

    if not users:
        st.info("No users found.")
        return

    _render_password_override(supabase, users)
    st.divider()
    _render_session_control(supabase, users)


def _render_password_override(supabase, users):
    st.markdown("##### 🔑 Override Password")
    usernames = [u["username"] for u in users]
    with st.form("admin_password_override_form", clear_on_submit=True):
        target_user = st.selectbox("Select User", usernames, key="pwd_override_user")
        new_pass = st.text_input("New Password", type="password", key="pwd_override_value").strip()
        submitted = st.form_submit_button("⚠️ OVERWRITE PASSWORD", use_container_width=True)

    if submitted:
        if throttled("admin_password_override"):
            st.warning("⏳ Action throttled. Please slow down.")
        elif not new_pass:
            st.error("❌ Password cannot be empty.")
        else:
            hashed = hashlib.sha256(new_pass.encode()).hexdigest()
            try:
                supabase.table("users").update({"password": hashed}).eq("username", target_user).execute()
                st.success(f"✅ Password overwritten for `@{target_user}`.")
            except Exception as e:
                st.error(f"❌ Database rejection: {e}")


def _render_session_control(supabase, users):
    st.markdown("##### 🛡️ Revoke & Terminate Sessions")
    st.caption("`Force Logout` clears the user's session on their next page load. `Revoked` blocks login entirely until cleared.")

    df = pd.DataFrame(users)
    for col in ["force_logout", "is_revoked"]:
        if col not in df.columns:
            df[col] = False

    keep_cols = [c for c in ["username", "name", "role", "role_id", "location_id", "force_logout", "is_revoked"] if c in df.columns]
    df_display = df[keep_cols].rename(columns={
        "username": "USERNAME", "name": "NAME", "role": "ROLE", "role_id": "ROLE",
        "location_id": "LOCATION", "force_logout": "FORCE LOGOUT", "is_revoked": "REVOKED",
    })
    df_display = df_display.loc[:, ~df_display.columns.duplicated()]

    disabled_cols = [c for c in df_display.columns if c not in ("FORCE LOGOUT", "REVOKED")]
    edited = st.data_editor(df_display, disabled=disabled_cols, hide_index=True, use_container_width=True, key="user_session_editor")

    if st.button("COMMIT ACCESS CHANGES", use_container_width=True, key="user_session_commit_btn"):
        if throttled("admin_session_commit"):
            st.warning("⏳ Action throttled. Please slow down.")
            return
        chg = 0
        for i in range(len(edited)):
            username = df_display.iloc[i]["USERNAME"]
            payload = {}
            if bool(df_display.iloc[i]["FORCE LOGOUT"]) != bool(edited.iloc[i]["FORCE LOGOUT"]):
                payload["force_logout"] = bool(edited.iloc[i]["FORCE LOGOUT"])
            if bool(df_display.iloc[i]["REVOKED"]) != bool(edited.iloc[i]["REVOKED"]):
                payload["is_revoked"] = bool(edited.iloc[i]["REVOKED"])
            if payload:
                try:
                    supabase.table("users").update(payload).eq("username", username).execute()
                    chg += 1
                except Exception as e:
                    st.error(f"❌ Failed to update `@{username}`: {e}")
        if chg > 0:
            st.success(f"✅ Synchronized {chg} account(s).")
            safe_rerun()

    with st.expander("ℹ️ Schema requirement"):
        st.code(
            "alter table users add column if not exists force_logout boolean default false;\n"
            "alter table users add column if not exists is_revoked boolean default false;",
            language="sql",
        )
        st.caption("Run this once in Supabase SQL editor. Until applied, toggling these has no effect.")

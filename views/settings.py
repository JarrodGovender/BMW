import hashlib
import streamlit as st
from config import safe_rerun, PHASEV_LOGO
from utils.theme_engine import render_logo


def render(supabase):
    st.markdown("## ⚙️ SETTINGS")

    t1, t2 = st.tabs(["🎨 APPEARANCE", "🔐 SECURITY"])

    with t1:
        _render_appearance()

    with t2:
        _render_security(supabase)


def _render_appearance():
    st.markdown("#### THEME")
    current = st.session_state.get('theme', 'Dark')
    choice = st.radio(
        "Select theme:", ["Dark", "Light"],
        index=0 if current == 'Dark' else 1,
        horizontal=True, label_visibility="collapsed", key="settings_theme_radio",
    )
    if choice != current:
        st.session_state['theme'] = choice
        safe_rerun()

    st.markdown("---")
    st.markdown("#### LOGO PREVIEW (Dynamic Logo Logic)")
    st.caption(
        "Light Mode wraps the Phase V mark in a black bounding box for contrast; "
        "Dark Mode renders it directly with no box."
    )
    render_logo(PHASEV_LOGO, height=40)

    st.markdown("---")
    with st.expander("⚙️ Advanced — Command Center data source"):
        demo_on = st.toggle(
            "Presentation Demo Data",
            value=st.session_state.get('presentation_mode', True),
            help="On: Command Center shows curated demo figures. Off: live Supabase data.",
            key="settings_presentation_toggle",
        )
        if demo_on != st.session_state.get('presentation_mode', True):
            st.session_state['presentation_mode'] = demo_on
            safe_rerun()
        st.caption("Live Supabase Data" if not demo_on else "Presentation Demo Data")


def _render_security(supabase):
    st.markdown("#### CHANGE PASSWORD")
    username = st.session_state.get('user')
    if not username:
        st.info("No active session.")
        return

    with st.form("settings_change_password"):
        current_pass = st.text_input("CURRENT PASSWORD", type="password")
        new_pass = st.text_input("NEW PASSWORD", type="password")
        confirm_pass = st.text_input("CONFIRM NEW PASSWORD", type="password")
        submitted = st.form_submit_button("🔐 UPDATE PASSWORD", use_container_width=True)

    if not submitted:
        return

    if not (current_pass and new_pass and confirm_pass):
        st.warning("Fill in all three fields.")
        return
    if new_pass != confirm_pass:
        st.error("New password and confirmation do not match.")
        return

    try:
        record = supabase.table("users").select("password").eq("username", username).execute().data
        if not record:
            st.error("User record not found.")
            return
        stored_hash = record[0].get('password')
        if hashlib.sha256(current_pass.encode()).hexdigest() != stored_hash:
            st.error("Current password is incorrect.")
            return

        new_hash = hashlib.sha256(new_pass.encode()).hexdigest()
        supabase.table("users").update({"password": new_hash}).eq("username", username).execute()
        st.success("✅ Password updated.")
    except Exception as e:
        st.error(f"Error: {e}")

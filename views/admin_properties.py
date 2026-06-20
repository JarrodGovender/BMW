"""Super User property & site management: full CRUD on property_sites plus a
site-level audit/visit log stored in property_notes (separate from the
task-level task_notes used by the day-to-day property workflow)."""
import streamlit as st
import pandas as pd

from config import safe_rerun
from utils.rate_limiter import throttled


def render(supabase, container_bg="#1c1c1c", text_color="#ffffff", theme="Dark"):
    st.subheader("🏗️ Property & Site Management")
    st.caption("Add, rename, or decommission physical sites, and log audit/visit notes against each.")

    _render_add_site(supabase)
    st.markdown("---")

    try:
        sites = supabase.table("property_sites").select("*").order("id", ascending=True).execute().data or []
    except Exception as e:
        st.error(f"❌ Could not load sites: {e}")
        return

    if not sites:
        st.info("No sites registered.")
        return

    for site in sites:
        with st.expander(f"📍 {site['site_name']}", expanded=False):
            _render_site_editor(supabase, site)
            st.markdown("---")
            _render_site_notes(supabase, site, container_bg, text_color, theme)


def _render_add_site(supabase):
    with st.expander("➕ ADD NEW PROPERTY SITE"):
        new_site_name = st.text_input("Official Site Name (e.g., BMW Dalpark)", key="admin_new_site_name")
        if st.button("CREATE SITE", key="admin_create_site_btn"):
            if throttled("admin_create_site"):
                st.warning("⏳ Action throttled. Please slow down.")
            elif not new_site_name.strip():
                st.warning("Site name cannot be blank.")
            else:
                try:
                    supabase.table("property_sites").insert({"site_name": new_site_name.strip()}).execute()
                    st.success("✅ Site added.")
                    safe_rerun()
                except Exception as e:
                    st.error(f"❌ Database rejection: {e}")


def _render_site_editor(supabase, site):
    site_id = site["id"]
    c1, c2 = st.columns([3, 1])
    renamed = c1.text_input("Site Name", value=site["site_name"], key=f"admin_rename_{site_id}")

    if c1.button("💾 SAVE NAME", key=f"admin_save_name_{site_id}"):
        if throttled(f"admin_save_name_{site_id}"):
            st.warning("⏳ Action throttled. Please slow down.")
        elif not renamed.strip():
            st.warning("Site name cannot be blank.")
        elif renamed.strip() != site["site_name"]:
            try:
                supabase.table("property_sites").update({"site_name": renamed.strip()}).eq("id", site_id).execute()
                st.success("✅ Updated.")
                safe_rerun()
            except Exception as e:
                st.error(f"❌ Database rejection: {e}")

    confirm_key = f"admin_confirm_delete_{site_id}"
    if c2.button("🗑️ DELETE SITE", key=f"admin_delete_btn_{site_id}"):
        st.session_state[confirm_key] = True

    if st.session_state.get(confirm_key):
        st.warning(f"⚠️ This permanently deletes **{site['site_name']}**. Confirm?")
        cc1, cc2 = st.columns(2)
        if cc1.button("✅ CONFIRM DELETE", key=f"admin_confirm_delete_btn_{site_id}"):
            if throttled(f"admin_delete_site_{site_id}"):
                st.warning("⏳ Action throttled. Please slow down.")
            else:
                try:
                    supabase.table("property_sites").delete().eq("id", site_id).execute()
                    st.session_state.pop(confirm_key, None)
                    st.success("✅ Site deleted.")
                    safe_rerun()
                except Exception as e:
                    st.error(f"❌ Database rejection: {e}")
        if cc2.button("CANCEL", key=f"admin_cancel_delete_{site_id}"):
            st.session_state.pop(confirm_key, None)
            safe_rerun()


def _render_site_notes(supabase, site, container_bg, text_color, theme):
    site_id = site["id"]
    st.markdown("##### 📝 Site Visit / Audit Log")

    try:
        notes = supabase.table("property_notes").select("*").eq("site_id", site_id).order("created_at", ascending=False).execute().data or []
    except Exception:
        notes = []

    if not notes:
        st.caption("No notes logged for this site yet.")
    for note in notes:
        author = note.get("author_name", "System")
        bg, border = ("#2b1c1c" if theme == "Dark" else "#ffe6e6", "#ff4b4b") if "(Director)" in author or "(Super User)" in author else (container_bg, text_color)
        st.markdown(
            f"<div style='background-color:{bg}; padding:8px; margin-bottom:5px; border-left:3px solid {border};'>"
            f"<small><b>{author}</b> — {str(note.get('created_at', '')).split('T')[0]}</small><br>{note.get('note_text', '')}</div>",
            unsafe_allow_html=True,
        )

    new_note = st.text_area("Log a visit, audit finding, or note...", key=f"admin_note_text_{site_id}")
    if st.button("📌 POST NOTE", key=f"admin_post_note_{site_id}"):
        if throttled(f"admin_post_note_{site_id}"):
            st.warning("⏳ Action throttled. Please slow down.")
        elif not new_note.strip():
            st.warning("Note cannot be blank.")
        else:
            author_name = f"{st.session_state.get('name', 'Super User')} (Super User)"
            try:
                supabase.table("property_notes").insert({
                    "site_id": site_id, "note_text": new_note.strip(), "author_name": author_name,
                }).execute()
                st.success("✅ Note logged.")
                safe_rerun()
            except Exception as e:
                st.error(f"❌ Database rejection (has `property_notes` been created? see SQL below): {e}")

    with st.expander("ℹ️ Schema requirement", expanded=False):
        st.code(
            "create table if not exists property_notes (\n"
            "    id bigint generated always as identity primary key,\n"
            "    site_id bigint references property_sites(id) on delete cascade,\n"
            "    note_text text not null,\n"
            "    author_name text,\n"
            "    created_at timestamptz default now()\n"
            ");",
            language="sql",
        )

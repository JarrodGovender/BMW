import streamlit as st
import pandas as pd
from config import safe_rerun

def render(supabase, container_bg, text_color, theme):
    st.markdown("### 🏢 PHASE V - PROPERTY MANAGEMENT CONSOLE")
    
    with st.expander("➕ ADD NEW PROPERTY SITE TO PORTFOLIO"):
        new_site_name = st.text_input("Enter Official Site Name (e.g., BMW Dalpark)")
        if st.button("CREATE SITE NODE"):
            if new_site_name:
                try: supabase.table("property_sites").insert({"site_name": new_site_name}).execute(); st.success(f"✅ Added."); safe_rerun()
                except Exception as e: st.error(f"Database Error: {e}")
            else: st.warning("Site name cannot be blank.")
    st.markdown("---")
    
    try: sites = supabase.table("property_sites").select("*").order("id", ascending=True).execute().data or []
    except: sites = []
        
    if not sites: st.info("No sites registered.")
    else:
        site_tabs = st.tabs([s['site_name'] for s in sites] + ["🗄️ ARCHIVED TASKS"])
        
        for idx, current_site in enumerate(sites):
            with site_tabs[idx]:
                site_id = current_site['id']
                col_add, _ = st.columns([1, 1])
                with col_add:
                    st.markdown("#### DEPLOY NEW TASK")
                    new_task_title = st.text_input("TASK TITLE", key=f"new_task_{site_id}")
                    new_task_desc = st.text_area("DETAILED DESCRIPTION", key=f"new_desc_{site_id}")
                    new_priority = st.selectbox("PRIORITY LEVEL", ["🔴 High", "🟡 Medium", "🟢 Low"], index=1, key=f"new_pri_{site_id}")
                    if st.button("CREATE TASK", key=f"btn_create_{site_id}"):
                        if new_task_title:
                            supabase.table("site_tasks").insert({"site_id": site_id, "task_title": new_task_title, "task_description": new_task_desc, "priority": new_priority, "created_by": st.session_state['name']}).execute(); safe_rerun()
                        else: st.warning("Task Title is required.")
                            
                st.markdown("<br><hr>", unsafe_allow_html=True)
                
                try: df_tasks = pd.DataFrame(supabase.table("site_tasks").select("*").eq("site_id", site_id).execute().data or [])
                except: df_tasks = pd.DataFrame()
                if not df_tasks.empty and 'is_archived' not in df_tasks.columns: df_tasks['is_archived'] = False
                df_active = df_tasks[df_tasks['is_archived'] != True] if not df_tasks.empty else pd.DataFrame()
                
                col_open, col_prog, col_arch = st.columns(3)
                for status, col, icon in [("Open", col_open, "⚪"), ("In Progress", col_prog, "🔵"), ("Completed", col_arch, "🏁")]:
                    with col:
                        st.markdown(f"#### {icon} {status.upper()}")
                        subset = df_active[df_active['status'] == status] if not df_active.empty else pd.DataFrame()
                        if subset.empty: st.caption("No tasks.")
                        else:
                            for _, task_row in subset.sort_values(by='created_at', ascending=False).iterrows():
                                task_id, pri_badge = task_row['id'], task_row.get('priority', '🟡 Medium')
                                with st.expander(f"{pri_badge.split()[0]} {task_row['task_title']}"):
                                    st.markdown(f"**Priority:** {pri_badge}")
                                    if task_row.get('task_description'): st.info(task_row['task_description'])
                                    st.caption(f"Created by: {task_row.get('created_by', 'System')} | {str(task_row['created_at']).split('T')[0]}")
                                    st.markdown("---")
                                    new_status = st.radio("Move to:", ["Open", "In Progress", "Completed"], index=["Open", "In Progress", "Completed"].index(status), horizontal=True, key=f"rad_{task_id}")
                                    if new_status != status:
                                        if st.button("UPDATE STATUS", key=f"upd_{task_id}"): supabase.table("site_tasks").update({"status": new_status}).eq("id", task_id).execute(); safe_rerun()
                                    if status == "Completed":
                                        if st.button("🗃️ MOVE TO ARCHIVE", key=f"arch_btn_{task_id}"): supabase.table("site_tasks").update({"is_archived": True}).eq("id", task_id).execute(); safe_rerun()
                                    st.markdown("---")
                                    try: notes_data = supabase.table("task_notes").select("*").eq("task_id", task_id).order("created_at", ascending=True).execute().data or []
                                    except: notes_data = []
                                    for note in notes_data:
                                        bg, border = ("#2b1c1c" if theme == 'Dark' else "#ffe6e6", "#ff4b4b") if "(Director)" in note['author_name'] else (container_bg, text_color)
                                        st.markdown(f"<div style='background-color:{bg}; padding:8px; margin-bottom:5px; border-left:3px solid {border};'><small><b>{note['author_name']}</b></small><br>{note['note_text']}</div>", unsafe_allow_html=True)
                                    new_note = st.text_input("Add update note...", key=f"note_in_{task_id}")
                                    if st.button("POST NOTE", key=f"note_btn_{task_id}") and new_note:
                                        supabase.table("task_notes").insert({"task_id": task_id, "note_text": new_note, "author_name": st.session_state['name']}).execute(); safe_rerun()

        with site_tabs[-1]:
            st.markdown("#### 🗄️ GLOBAL ARCHIVED TASKS")
            try: df_archived = pd.DataFrame(supabase.table("site_tasks").select("*").eq("is_archived", True).order("created_at", ascending=False).execute().data or [])
            except: df_archived = pd.DataFrame()
            if df_archived.empty: st.info("No tasks have been moved to the archive yet.")
            else:
                site_mapping = {s['id']: s['site_name'] for s in sites}
                df_archived['site_name'] = df_archived['site_id'].map(site_mapping)
                for _, a_row in df_archived.iterrows():
                    t_id = a_row['id']
                    with st.expander(f"🗃️ [{str(a_row.get('site_name', 'Unknown')).upper()}] {str(a_row.get('priority', '🟡 Medium')).split()[0]} {a_row['task_title']}"):
                        st.markdown(f"**Archived Status:** {a_row['status']} | **Priority:** {a_row.get('priority', 'Medium')}")
                        if a_row.get('task_description'): st.info(a_row['task_description'])
                        if st.button("⏪ UNARCHIVE TASK", key=f"unarch_{t_id}"): supabase.table("site_tasks").update({"is_archived": False}).eq("id", t_id).execute(); safe_rerun()
                        st.markdown("---")
                        try: notes_data = supabase.table("task_notes").select("*").eq("task_id", t_id).order("created_at", ascending=True).execute().data or []
                        except: notes_data = []
                        for note in notes_data:
                            bg, border = ("#2b1c1c" if theme == 'Dark' else "#ffe6e6", "#ff4b4b") if "(Director)" in note['author_name'] else (container_bg, text_color)
                            st.markdown(f"<div style='background-color:{bg}; padding:8px; margin-bottom:5px; border-left:3px solid {border};'><small><b>{note['author_name']}</b></small><br>{note['note_text']}</div>", unsafe_allow_html=True)

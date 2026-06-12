import streamlit as st
import pandas as pd
from config import safe_rerun

def render(supabase, container_bg, text_color, metric_label, theme):
    dir_tab1, dir_tab2 = st.tabs(["📈 EXECUTIVE DASHBOARD", "🗄️ ARCHIVED TASKS"])
    
    try:
        df_s = pd.DataFrame(supabase.table("property_sites").select("*").execute().data or [])
        df_t = pd.DataFrame(supabase.table("site_tasks").select("*").order("created_at", ascending=False).execute().data or [])
    except: df_s, df_t = pd.DataFrame(), pd.DataFrame()
        
    if not df_t.empty and 'is_archived' not in df_t.columns: df_t['is_archived'] = False

    with dir_tab1:
        st.markdown("### 📈 PHASE V - EXECUTIVE PORTFOLIO DASHBOARD")
        if df_s.empty or df_t.empty: st.info("Insufficient data.")
        else:
            df_active = df_t[df_t['is_archived'] != True].copy()
            total_sites, total_tasks = len(df_s), len(df_active)
            completed_tasks = len(df_active[df_active['status'] == 'Completed'])
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("PORTFOLIO SITES", total_sites)
            m2.metric("ACTIVE NETWORK TASKS", total_tasks)
            m3.metric("ACTIVE COMPLETION RATE", f"{completion_rate:.1f}%")
            
            st.markdown("---")
            st.markdown("#### 📊 TASK DISTRIBUTION BY PROPERTY")
            df_s_clean = df_s[['id', 'site_name']].rename(columns={'id': 'site_id'})
            df_active = df_active.merge(df_s_clean, on='site_id', how='left')
            pivot_df = pd.crosstab(df_active['site_name'], df_active['status'])
            for col in ["Open", "In Progress", "Completed"]:
                if col not in pivot_df.columns: pivot_df[col] = 0
            st.bar_chart(pivot_df[["Open", "In Progress", "Completed"]])
            
            st.markdown("---")
            st.markdown("#### 🔎 PORTFOLIO TASK DRILL-DOWN")
            dir_c1, dir_c2, dir_c3 = st.columns([2, 1, 1])
            site_filter = dir_c1.selectbox("FILTER BY PROPERTY", ["All Sites"] + df_s['site_name'].tolist())
            status_filter = dir_c2.selectbox("STATUS", ["All", "Open", "In Progress", "Completed"])
            pri_filter = dir_c3.selectbox("PRIORITY", ["All", "🔴 High", "🟡 Medium", "🟢 Low"])
            
            drill_df = df_active.copy()
            if site_filter != "All Sites": drill_df = drill_df[drill_df['site_name'] == site_filter]
            if status_filter != "All": drill_df = drill_df[drill_df['status'] == status_filter]
            if pri_filter != "All": drill_df = drill_df[drill_df['priority'] == pri_filter]
            
            st.markdown("<br>", unsafe_allow_html=True)
            if drill_df.empty: st.success("No active tasks match filters.")
            else:
                for _, task_row in drill_df.sort_values(by='created_at', ascending=False).iterrows():
                    task_id = task_row['id']
                    s_icon = "🏁" if task_row['status'] == "Completed" else ("🔵" if task_row['status'] == "In Progress" else "⚪")
                    
                    with st.expander(f"{s_icon} [{str(task_row.get('site_name','Unknown')).upper()}] {str(task_row.get('priority', '🟡 Medium')).split()[0]} {task_row['task_title']}"):
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.markdown(f"**Current Status:** {task_row['status']}"); st.markdown(f"**Priority:** {task_row.get('priority', 'Medium')}")
                        with col_info2:
                            st.markdown(f"**Delegated By:** {task_row.get('created_by', 'System')}"); st.markdown(f"**Logged:** {str(task_row['created_at']).split('T')[0]}")
                        if pd.notna(task_row.get('task_description')) and task_row.get('task_description'): st.info(task_row['task_description'])
                        st.markdown("---"); st.markdown("##### 📋 AUDIT & DIRECTIVE TRAIL")
                        try: notes_data = supabase.table("task_notes").select("*").eq("task_id", task_id).order("created_at", ascending=True).execute().data or []
                        except: notes_data = []
                        for note in notes_data:
                            bg, border = ("#2b1c1c" if theme == 'Dark' else "#ffe6e6", "#ff4b4b") if "(Director)" in note['author_name'] else (container_bg, text_color)
                            st.markdown(f"<div style='background-color:{bg}; padding:10px; margin-bottom:8px; border-left:4px solid {border};'><small style='color:{metric_label};'><b>{note['author_name']}</b></small><br>{note['note_text']}</div>", unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        new_dir_note = st.text_area("APPEND DIRECTIVE", key=f"dir_note_in_{task_id}")
                        if st.button("ISSUE DIRECTIVE", key=f"dir_note_btn_{task_id}") and new_dir_note:
                            supabase.table("task_notes").insert({"task_id": int(task_id), "note_text": new_dir_note, "author_name": f"{st.session_state['name']} (Director)"}).execute(); safe_rerun()

    with dir_tab2:
        st.markdown("### 🗄️ EXECUTIVE ARCHIVE LEDGER")
        if not df_t.empty:
            df_arch = df_t[df_t['is_archived'] == True].copy()
            if not df_arch.empty:
                df_arch = df_arch.merge(df_s[['id', 'site_name']].rename(columns={'id': 'site_id'}), on='site_id', how='left').sort_values(by='created_at', ascending=False)
                for _, a_row in df_arch.iterrows():
                    t_id = a_row['id']
                    with st.expander(f"🗃️ [{str(a_row.get('site_name', 'Unknown')).upper()}] {str(a_row.get('priority', '🟡 Medium')).split()[0]} {a_row['task_title']}"):
                        st.markdown(f"**Status:** {a_row['status']} | **Priority:** {a_row.get('priority', 'Medium')}")
                        if a_row.get('task_description'): st.info(a_row['task_description'])
                        if st.button("⏪ UNARCHIVE TASK", key=f"dir_unarch_{t_id}"): supabase.table("site_tasks").update({"is_archived": False}).eq("id", t_id).execute(); safe_rerun()
                        st.markdown("---")
                        try: notes_data = supabase.table("task_notes").select("*").eq("task_id", t_id).order("created_at", ascending=True).execute().data or []
                        except: notes_data = []
                        for note in notes_data:
                            bg, border = ("#2b1c1c" if theme == 'Dark' else "#ffe6e6", "#ff4b4b") if "(Director)" in note['author_name'] else (container_bg, text_color)
                            st.markdown(f"<div style='background-color:{bg}; padding:8px; margin-bottom:5px; border-left:3px solid {border};'><small><b>{note['author_name']}</b></small><br>{note['note_text']}</div>", unsafe_allow_html=True)
                        new_dir_note = st.text_area("APPEND NOTE", key=f"arch_note_in_{t_id}")
                        if st.button("POST NOTE", key=f"arch_note_btn_{t_id}") and new_dir_note:
                            supabase.table("task_notes").insert({"task_id": int(t_id), "note_text": new_dir_note, "author_name": f"{st.session_state['name']} (Director)"}).execute(); safe_rerun()
            else: st.info("No archives.")
